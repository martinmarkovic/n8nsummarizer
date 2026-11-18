"""
tiny-voca TTS backend — local neural text-to-speech (English, F2/M2 voices).

Implements the same public surface as ``tts_engine_pyttsx3`` so the two can be
swapped by the ``tts_engine`` facade:

    speak(text, ...), stop(), is_available(), is_speaking(), get_voices()

Synthesis runs in a daemon thread; playback uses the Windows ``winsound``
module. Because Windows does not allow ``SND_MEMORY`` together with
``SND_ASYNC``, the WAV is written to a short-lived temp file and played with
``SND_FILENAME | SND_ASYNC``. ``stop()`` purges the sound and sets a cancel
event that aborts synthesis between sentences.

All heavy imports (onnxruntime, numpy, dizione, huggingface-hub) are lazy so
the module is safe to import even before the new dependencies are installed.
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)

# --- state ------------------------------------------------------------------

_state_lock = threading.Lock()
_current_thread = None
_is_speaking = False
_cancel_event = None
_current_wav_path = None
_model = None
_generation = 0            # bumped per speak(); used to invalidate stale timers
_prepare_thread_started = False
_prepare_lock = threading.Lock()


def _get_model():
    """Return the shared TinyVocaModel, creating it on first use."""
    global _model
    if _model is None:
        from models.tts.tiny_voca import TinyVocaModel
        _model = TinyVocaModel()
    return _model


# --- API --------------------------------------------------------------------

def is_available() -> bool:
    """True when the tiny-voca model is downloaded and deps are importable."""
    model = _get_model()
    if not model.assets_present():
        return False
    try:
        model._import_deps()  # noqa: SLF001 - raises if a dep is missing
    except Exception:
        return False
    return True


def prepare_async(progress_cb=None):
    """Download the model in the background if it is not already present.

    Safe to call repeatedly; only one prepare thread runs at a time.
    """
    global _prepare_thread_started
    model = _get_model()
    if model.assets_present():
        if progress_cb:
            progress_cb("tiny-voca model ready")
        return

    with _prepare_lock:
        if _prepare_thread_started:
            return
        _prepare_thread_started = True

    def _worker():
        model.ensure_assets(progress_cb=progress_cb)

    threading.Thread(target=_worker, daemon=True).start()


def get_voices() -> list:
    """Return the tiny-voca voice ids (F2, M2)."""
    model = _get_model()
    return model.voices


def speak(text, voice="F2", speed=1.0, pitch_shift=0.0, pitch_range=1.0):
    """Synthesize and play ``text`` asynchronously."""
    global _current_thread, _is_speaking, _cancel_event, _generation

    if not text or not text.strip():
        logger.warning("Cannot speak empty text")
        return

    if not is_available():
        logger.warning("tiny-voca not available")
        return

    logger.info(f"Speaking (tiny-voca): {text[:50]}{'...' if len(text) > 50 else ''}")

    stop()

    with _state_lock:
        _generation += 1
        _cancel_event = threading.Event()

    def _speak_thread():
        global _is_speaking

        with _state_lock:
            _is_speaking = True
            cancel = _cancel_event

        # If a stop landed before we captured the event, treat it as cancelled.
        if cancel is None:
            cancel = threading.Event()
            cancel.set()

        playback_started = False
        try:
            from models.tts.tiny_voca import NothingToPronounce

            model = _get_model()
            if not model.load():
                logger.error(f"tiny-voca load failed: {model.last_error}")
                return

            audio = model.text_to_audio(
                text,
                voice=voice,
                speed=speed,
                pitch_shift=pitch_shift,
                pitch_range=pitch_range,
                cancel_event=cancel,
            )

            if cancel.is_set():
                return

            wav_bytes = model.audio_to_wav_bytes(audio, model.sample_rate)

            if cancel.is_set():
                return

            with _state_lock:
                gen = _generation

            path = _play_wav(wav_bytes)
            if path:
                playback_started = True
                _schedule_done(len(audio), model.sample_rate, gen, path)

            logger.info("Speech completed (tiny-voca)")

        except NothingToPronounce as exc:
            logger.info(f"tiny-voca: nothing to pronounce: {exc}")
        except Exception as exc:
            logger.error(f"Error during tiny-voca speech: {exc}")
        finally:
            if not playback_started:
                with _state_lock:
                    _is_speaking = False

    with _state_lock:
        _current_thread = threading.Thread(target=_speak_thread, daemon=True)
        _current_thread.start()


def stop() -> None:
    """Stop synthesis/playback immediately."""
    global _is_speaking, _cancel_event

    with _state_lock:
        event = _cancel_event
        _is_speaking = False
        _cancel_event = None

    if event is not None:
        event.set()

    _purge_playback()
    _delete_current_wav()


def is_speaking() -> bool:
    return _is_speaking


# --- playback / timing (Windows winsound) -----------------------------------

def _play_wav(wav_bytes):
    """Write ``wav_bytes`` to a temp file and play it asynchronously.

    Returns the temp file path on success, or None on failure.
    """
    global _current_wav_path

    try:
        import tempfile
        import winsound
    except Exception as exc:
        logger.warning(f"winsound unavailable; cannot play audio: {exc}")
        return None

    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as fh:
            fh.write(wav_bytes)

        winsound.PlaySound(
            path,
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except Exception as exc:
        logger.error(f"winsound playback failed: {exc}")
        if path:
            try:
                os.remove(path)
            except OSError:
                pass
        return None

    with _state_lock:
        _current_wav_path = path
    return path


def _purge_playback():
    try:
        import winsound
    except Exception:
        return
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass


def _delete_current_wav():
    """Remove the current temp WAV file, if any."""
    global _current_wav_path
    with _state_lock:
        path = _current_wav_path
        _current_wav_path = None
    if path:
        try:
            os.remove(path)
        except OSError:
            pass


def _schedule_done(num_samples, sample_rate, generation, path):
    """Clear ``_is_speaking`` and delete the temp file once playback finishes.

    ``generation`` guards against a stale timer clearing the flag (or deleting
    a file) after a newer utterance has already started.
    """
    global _is_speaking
    duration = float(num_samples) / float(sample_rate)

    def _on_done():
        global _is_speaking, _current_wav_path
        with _state_lock:
            if _generation != generation:
                return
            _is_speaking = False
        if path:
            try:
                os.remove(path)
            except OSError:
                pass
            with _state_lock:
                if _current_wav_path == path:
                    _current_wav_path = None

    timer = threading.Timer(duration + 0.2, _on_done)
    timer.daemon = True
    timer.start()
