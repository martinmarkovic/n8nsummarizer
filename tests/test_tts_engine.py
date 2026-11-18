#!/usr/bin/env python3
"""
Tests for the local tiny-voca TTS engine and facade routing (v16.1).

These tests exercise the torch-free pieces that run without onnxruntime /
dizione / huggingface-hub: text helpers, WAV encoding, model-dir resolution,
and the provider facade. The heavy inference path is not exercised here.
"""

import os
import sys
from unittest.mock import patch

# Ensure the project root is importable (models/, utils/, controllers/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """The facade and backends import without pulling in the heavy deps."""
    import utils.tts_engine
    import utils.tts_engine_tinyvoca
    import utils.tts_engine_pyttsx3
    import models.tts.tiny_voca

    assert hasattr(utils.tts_engine, "speak")
    assert hasattr(utils.tts_engine, "stop")
    assert hasattr(utils.tts_engine_tinyvoca, "is_available")
    return True


def test_sentence_splitting():
    """Sentence splitter and trailing-full-stop helpers match the reference."""
    from models.tts.tiny_voca import sentences, finished

    parts = sentences("Hello world. How are you? I'm fine!")
    assert len(parts) == 3, parts

    # "Mr." must not be treated as a sentence break.
    parts = sentences("Mr. Smith went home.")
    assert len(parts) == 1, parts

    # Text without a final mark gets a full stop.
    assert finished("see you soon") == "see you soon."
    assert finished("Hello!") == "Hello!"
    return True


def test_shorter():
    from models.tts.tiny_voca import shorter

    assert len(shorter("a long sentence, with a comma")) > 1
    assert shorter("singleword") == []
    return True


def test_peak_limiting():
    try:
        import numpy as np
    except ImportError:
        print("[SKIP] numpy not installed")
        return True

    from models.tts.tiny_voca import limit_peak, PEAK

    loud = np.array([0.0, 1.5, -1.2], dtype=np.float32)
    out = limit_peak(loud)
    assert float(abs(out).max()) <= PEAK + 1e-6

    quiet = np.array([0.1, -0.2], dtype=np.float32)
    assert float(abs(limit_peak(quiet)).max()) < 1.0
    return True


def test_wav_encoding():
    try:
        import numpy as np
    except ImportError:
        print("[SKIP] numpy not installed")
        return True

    from models.tts.tiny_voca import TinyVocaModel

    audio = np.zeros(2400, dtype=np.float32)  # 0.1 s at 24 kHz
    data = TinyVocaModel.audio_to_wav_bytes(audio, 24000)
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"
    return True


def test_default_model_dir():
    from models.tts.tiny_voca import default_model_dir

    with patch.dict(os.environ, {"TTS_MODEL_DIR": "C:/custom/tts"}, clear=False):
        assert str(default_model_dir()).endswith("custom/tts") or "custom" in str(default_model_dir())

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TTS_MODEL_DIR", None)
        assert str(default_model_dir())
    return True


def test_facade_provider_routing():
    from utils import tts_engine
    from utils import tts_engine_tinyvoca, tts_engine_pyttsx3

    # tinyvoca available → tinyvoca speaks
    with patch.object(tts_engine_tinyvoca, "is_available", return_value=True), \
         patch.object(tts_engine_tinyvoca, "speak") as tv_speak:
        with patch.dict(os.environ, {"TTS_PROVIDER": "tinyvoca"}, clear=False):
            tts_engine.speak("hello")
        tv_speak.assert_called_once()

    # tinyvoca unavailable → fallback to system + warm up download
    with patch.object(tts_engine_tinyvoca, "is_available", return_value=False), \
         patch.object(tts_engine_tinyvoca, "prepare_async") as prep, \
         patch.object(tts_engine_pyttsx3, "speak") as sys_speak:
        with patch.dict(os.environ, {"TTS_PROVIDER": "tinyvoca"}, clear=False):
            tts_engine.speak("hello")
        sys_speak.assert_called_once()
        prep.assert_called_once()

    # explicit system provider → system speaks, no download
    with patch.object(tts_engine_tinyvoca, "prepare_async") as prep, \
         patch.object(tts_engine_pyttsx3, "speak") as sys_speak:
        with patch.dict(os.environ, {"TTS_PROVIDER": "system"}, clear=False):
            tts_engine.speak("hello")
        sys_speak.assert_called_once()
        prep.assert_not_called()
    return True


def test_facade_stop():
    from utils import tts_engine
    from utils import tts_engine_tinyvoca, tts_engine_pyttsx3

    with patch.object(tts_engine_tinyvoca, "stop") as a, \
         patch.object(tts_engine_pyttsx3, "stop") as b:
        tts_engine.stop()
        a.assert_called_once()
        b.assert_called_once()
    return True


def main():
    print("=" * 70)
    print("Testing tiny-voca TTS engine (v16.1)")
    print("=" * 70)

    tests = [
        test_imports,
        test_sentence_splitting,
        test_shorter,
        test_peak_limiting,
        test_wav_encoding,
        test_default_model_dir,
        test_facade_provider_routing,
        test_facade_stop,
    ]

    results = []
    for test in tests:
        name = test.__name__
        try:
            ok = test()
            results.append(bool(ok))
            print(f"[{'OK' if ok else 'FAILED'}] {name}")
        except Exception as exc:  # noqa: BLE001
            results.append(False)
            print(f"[FAILED] {name}: {exc}")
            import traceback
            traceback.print_exc()

    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 70)
    print(f"[{'SUCCESS' if passed == total else 'FAILED'}] {passed}/{total} tests passed")
    print("=" * 70)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
