"""
Local tiny-voca TTS model wrapper (ONNX Runtime).

Downloads/caches the ``n4ze3m/tiny-voca`` assets and exposes a thin, torch-free
inference path that turns text into 24 kHz mono float32 audio.

The text-processing helpers (sentence splitting, trailing full stop, long
utterance chunking, peak limiting) are vendored from the reference
``tiny_voca/infer.py`` (Apache-2.0, (c) Muhammed Nazeem) so the behaviour
matches the official Python/ONNX pipeline without importing PyTorch.
"""

import json
import os
import re
import threading
from pathlib import Path

from utils.logger import logger

# --- Model identity ---------------------------------------------------------

REPO_ID = "n4ze3m/tiny-voca"
CONFIG_REL = "config.json"
ONNX_REL = "onnx/model.onnx"
PHONEMIZER_REL = "phonemizer"

# SHA256 of onnx/model.onnx, from the model card.
ONNX_SHA256 = "fe6d918791a15b82e37465981d7f27a070e46b46635e5a3482fc8dff87a1ae46"

# Environment variable that tells ``dizione`` where its data lives.
DIZIONE_DATA_ENV = "DIZIONE_DATA"

# Loudest sample the produced audio is scaled to before writing 16-bit samples.
PEAK = 0.99
# Said when no sentence of a text could be read.
ENGLISH_ONLY = "tiny-voca only reads English for now"

# --- Vendored text helpers (from n4ze3m/tiny-voca src/tiny_voca/infer.py) ----

_SPACE = re.compile("[\\s" + chr(0xFEFF) + "]+")
_SENTENCE_END = re.compile(
    r"""(?:(?<=[.!?…])|(?<=[.!?…]["')\]]))\s+(?=["'(\[]?[A-Z0-9])"""
)
_NOT_AN_END = re.compile(
    r"(?:\b(?:mr|mrs|ms|dr|prof|sr|jr|st|vs|etc|no|inc|ltd|co|e\.g|i\.e|a\.m|p\.m)|\b[A-Z])\.$",
    re.IGNORECASE | re.ASCII,
)
_CLAUSE_END = re.compile(r"(?<=[,;:—])\s+")
_TEXT_END = re.compile("[\\s" + chr(0xFEFF) + "]+$")
_CLOSING = "\"'”’)]»"


class NothingToPronounce(Exception):
    """Raised when none of the text could be converted to speech."""


def sentences(text):
    """Split ``text`` into pronounceable sentences (mirrors the reference)."""
    parts, current = [], ""
    for piece in _SENTENCE_END.split(_SPACE.sub(" ", text).strip()):
        current = f"{current} {piece}" if current else piece
        if not _NOT_AN_END.search(current):
            parts.append(current)
            current = ""
    if current:
        parts.append(current)
    return [part for part in parts if any(char.isalnum() for char in part)]


def finished(text):
    """Append a full stop when ``text`` ends without a sentence mark."""
    body = _TEXT_END.sub("", text)
    if not body:
        return text
    last = _SPACE.split(body)[-1]
    if any(char.isalnum() for char in last):
        marked = last.rstrip(_CLOSING)[-1:] in tuple(".!?…,;:")
    else:
        marked = any(char in ".!?…" for char in last) or last in (",", ";", ":")
    return text if marked else body + "."


def shorter(text):
    """Split ``text`` into smaller pieces (after commas, else in half)."""
    pieces = _CLAUSE_END.split(text)
    if len(pieces) > 1:
        return pieces
    words = text.split(" ")
    if len(words) < 2:
        return []
    half = (len(words) + 1) // 2
    return [" ".join(words[:half]), " ".join(words[half:])]


def limit_peak(wave, peak=PEAK):
    """Scale the whole waveform down when its loudest sample is above ``peak``."""
    if wave.size == 0:
        return wave
    loudest = float(abs(wave).max())
    return wave * (peak / loudest) if loudest > peak else wave


# --- Model directory --------------------------------------------------------

def default_model_dir() -> Path:
    """Return the directory that holds (or will hold) the model assets."""
    override = os.environ.get("TTS_MODEL_DIR", "").strip()
    if override:
        return Path(override)

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "n8nsummarizer" / "models" / "tiny-voca"

    # Last resort: alongside the project source.
    return Path(__file__).resolve().parent.parent.parent / "models" / "tiny-voca"


# --- Wrapper ----------------------------------------------------------------

class TinyVocaModel:
    """Lazy-loading, torch-free tiny-voca inference via ONNX Runtime."""

    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir) if model_dir else default_model_dir()
        self._lock = threading.Lock()
        self._session = None
        self._config = None
        self._speakers = None
        self._dizione = None
        self._load_error = None

    # -- asset helpers -------------------------------------------------------

    @property
    def onnx_path(self) -> Path:
        return self.model_dir / ONNX_REL

    @property
    def config_path(self) -> Path:
        return self.model_dir / CONFIG_REL

    @property
    def phonemizer_dir(self) -> Path:
        return self.model_dir / PHONEMIZER_REL

    def assets_present(self) -> bool:
        return (
            self.onnx_path.exists()
            and self.config_path.exists()
            and self.phonemizer_dir.is_dir()
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        import hashlib
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def ensure_assets(self, progress_cb=None, cancel_event=None) -> bool:
        """Download missing assets; return True once the model is usable.

        ``progress_cb(status: str)`` is invoked at key milestones. It is called
        from whatever thread calls this method (the caller marshals to the UI).
        ``cancel_event``, when given and set, aborts before starting.
        """
        if self.assets_present():
            return True

        if cancel_event is not None and cancel_event.is_set():
            return False

        try:
            from huggingface_hub import snapshot_download
        except Exception as exc:  # pragma: no cover - dependency absent
            logger.warning(f"huggingface-hub unavailable for tiny-voca: {exc}")
            return False

        if progress_cb:
            progress_cb("Downloading tiny-voca model…")
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(
                repo_id=REPO_ID,
                local_dir=str(self.model_dir),
                allow_patterns=["config.json", "onnx/*", "phonemizer/*"],
            )
        except Exception as exc:
            logger.error(f"tiny-voca download failed: {exc}")
            if progress_cb:
                progress_cb(f"Download failed: {exc}")
            return False

        # Verify the ONNX checksum (the model card publishes a SHA256).
        try:
            actual = self._sha256(self.onnx_path)
            if actual.lower() != ONNX_SHA256.lower():
                logger.error(
                    f"tiny-voca ONNX checksum mismatch: expected {ONNX_SHA256}, got {actual}"
                )
                return False
        except Exception as exc:
            logger.error(f"tiny-voca ONNX checksum verification failed: {exc}")
            return False

        if progress_cb:
            progress_cb("tiny-voca model ready")
        return self.assets_present()

    # -- loading -------------------------------------------------------------

    def _import_deps(self):
        """Lazily import onnxruntime, numpy and dizione; raise on failure."""
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
        import dizione  # noqa: F401

        return onnxruntime, numpy, dizione

    def load(self, force=False):
        """Load the ONNX session, config and phonemizer (idempotent)."""
        with self._lock:
            if self._session is not None and not force:
                return True
            self._session = None
            self._load_error = None

            if not self.assets_present():
                self._load_error = "tiny-voca model files not present"
                logger.warning(self._load_error)
                return False

            try:
                onnxruntime, numpy, dizione = self._import_deps()
            except Exception as exc:
                self._load_error = f"tiny-voca dependencies missing: {exc}"
                logger.warning(self._load_error)
                return False

            # Point dizione at the phonemizer data before using it.
            os.environ[DIZIONE_DATA_ENV] = str(self.phonemizer_dir)

            try:
                with open(self.config_path, "r", encoding="utf-8") as fh:
                    self._config = json.load(fh)
                self._speakers = list(self._config.get("voices") or self._config.get("model", {}).get("speakers") or ["F2", "M2"])
                self._session = onnxruntime.InferenceSession(
                    str(self.onnx_path),
                    providers=["CPUExecutionProvider"],
                )
                self._dizione = dizione
            except Exception as exc:
                self._load_error = f"tiny-voca load failed: {exc}"
                logger.error(self._load_error)
                self._session = None
                return False

            return True

    @property
    def last_error(self):
        return self._load_error

    @property
    def sample_rate(self):
        if self._config is None:
            return 24000
        return int(self._config.get("sample_rate", 24000))

    @property
    def max_tokens(self):
        if self._config is None:
            return 512
        return int(
            self._config.get("model", {}).get("max_tokens", self._config.get("max_tokens", 512))
        )

    @property
    def voices(self):
        return list(self._speakers) if self._speakers else ["F2", "M2"]

    # -- inference -----------------------------------------------------------

    def _voice_index(self, voice):
        if self._speakers and voice in self._speakers:
            return self._speakers.index(voice)
        return 0 if voice == "F2" else 1

    def _phonemize(self, text):
        phones = self._dizione.phonemize(text)
        if not phones or not getattr(phones, "ids", None):
            raise NothingToPronounce(text)
        return phones

    def _utterance(self, phones, voice, speed, pitch_shift, seed, pitch_range):
        import numpy as np

        tokens = np.array([list(phones.ids)], dtype=np.int64)
        stress = np.array([list(phones.stress)], dtype=np.int64)
        voice_arr = np.array([self._voice_index(voice)], dtype=np.int64)
        speed_arr = np.array([float(speed)], dtype=np.float32)
        pitch_shift_arr = np.array([float(pitch_shift)], dtype=np.float32)
        pitch_range_arr = np.array([float(pitch_range)], dtype=np.float32)

        audio, _durations = self._session.run(
            None,
            {
                "tokens": tokens,
                "stress": stress,
                "voice": voice_arr,
                "speed": speed_arr,
                "pitch_shift": pitch_shift_arr,
                "pitch_range": pitch_range_arr,
            },
        )
        wave = audio[0]
        if not np.isfinite(wave).all():
            raise RuntimeError("tiny-voca produced non-finite audio")
        return wave

    def text_to_audio(
        self,
        text,
        voice="F2",
        speed=1.0,
        pitch_shift=0.0,
        pitch_range=1.0,
        seed=0,
        cancel_event=None,
    ):
        """Turn text of any length into a float32 mono array at ``sample_rate``.

        Reads sentence by sentence, joins the audio, and peak-limits to ``PEAK``.
        Raises ``NothingToPronounce`` when nothing could be read.
        """
        import numpy as np

        limit = self.max_tokens - 12
        waves = []

        def read(piece):
            if cancel_event is not None and cancel_event.is_set():
                return
            try:
                phones = self._phonemize(piece)
            except NothingToPronounce:
                return
            if len(phones.ids) <= limit:
                try:
                    waves.append(
                        self._utterance(
                            phones, voice, speed, pitch_shift, seed + len(waves), pitch_range
                        )
                    )
                except Exception:
                    # Fall through to shorter() splitting on the next attempt.
                    pass
                else:
                    return
            pieces = shorter(piece)
            if not pieces:
                raise ValueError(f"one word is too long to speak: {piece[:40]!r}")
            for part in pieces:
                read(part)

        for sentence in sentences(finished(text)):
            if cancel_event is not None and cancel_event.is_set():
                break
            read(sentence)

        if not waves:
            raise NothingToPronounce(f"nothing in the text could be read: {ENGLISH_ONLY}")

        wave = np.concatenate(waves) if len(waves) > 1 else waves[0]
        return limit_peak(wave, PEAK)

    @staticmethod
    def audio_to_wav_bytes(audio, sample_rate=24000):
        """Encode a float32 mono array as a 16-bit PCM WAV ``bytes`` object."""
        import io
        import wave

        import numpy as np

        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(sample_rate))
            wav.writeframes(pcm.tobytes())
        return buf.getvalue()
