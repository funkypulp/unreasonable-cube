# voice.py — microphone input, wake word, Whisper STT, TTS output
#
# STT: uses openai-whisper (more reliable than faster-whisper)
# TTS: uses macOS built-in `say` command
#
# Install: pip install openai-whisper sounddevice numpy
#
# Test this file directly:
#   python voice.py

import numpy as np
import sys
import platform
import subprocess
from config import (
    WAKE_PHRASE, WHISPER_MODEL, SILENCE_SEC,
    MAX_RECORD_SEC, SAMPLE_RATE
)


# ── Helpers ───────────────────────────────────────────────────────

def _require(package, install_name=None):
    import importlib
    try:
        return importlib.import_module(package)
    except ImportError:
        name = install_name or package
        print(f"\n[ERROR] Missing package: {name}")
        print(f"  Fix: pip install {name}\n")
        sys.exit(1)

def _is_mac():
    return platform.system() == "Darwin"


# ── Whisper setup ─────────────────────────────────────────────────

_whisper_model = None

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        whisper = _require("whisper", "openai-whisper")
        print(f"[voice] Loading Whisper model '{WHISPER_MODEL}'...")
        _whisper_model = whisper.load_model("tiny.en")
        print("[voice] Whisper ready.")
    return _whisper_model

def preload():
    """Load Whisper at startup so first transcription isn't slow."""
    _get_whisper()


# ── Recording ─────────────────────────────────────────────────────

def record_fixed(duration: float) -> np.ndarray:
    """Record a fixed-duration clip. Used for wake word detection."""
    sd = _require("sounddevice")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    return audio.flatten()


def record_until_silence() -> np.ndarray:
    """
    Record from mic until SILENCE_SEC of quiet, then stop.
    Returns full audio as a numpy array.
    """
    sd = _require("sounddevice")

    chunk_sec     = 0.3
    chunk_size    = int(SAMPLE_RATE * chunk_sec)
    silence_rms   = 0.015  # raised for noisy rooms
    max_chunks    = int(MAX_RECORD_SEC / chunk_sec)
    min_chunks    = int(0.5 / chunk_sec)
    silent_needed = int(SILENCE_SEC / chunk_sec)

    chunks       = []
    silent_count = 0
    has_speech   = False

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="float32"
    )

    print("[voice] 🎤 Recording... (speak, then pause to finish)")

    with stream:
        while len(chunks) < max_chunks:
            try:
                chunk, _ = stream.read(chunk_size)
            except KeyboardInterrupt:
                print("\n[voice] Recording interrupted.")
                raise
            flat = chunk.flatten()
            chunks.append(flat)

            rms = float(np.sqrt(np.mean(flat ** 2)))

            if rms > silence_rms:
                has_speech   = True
                silent_count = 0
            elif has_speech and len(chunks) > min_chunks:
                silent_count += 1
                if silent_count >= silent_needed:
                    break

    audio = np.concatenate(chunks)
    duration = len(audio) / SAMPLE_RATE
    print(f"[voice] ✓ Recording complete ({duration:.1f}s).")
    return audio


# ── Transcription ─────────────────────────────────────────────────

def transcribe(audio: np.ndarray) -> str:
    """
    Transcribe audio using openai-whisper.
    Returns transcript string.
    """
    print("[voice] Transcribing...")
    model = _get_whisper()

    # openai-whisper expects float32, normalized to [-1, 1]
    audio = audio.astype(np.float32)
    if audio.max() > 1.0:
        audio = audio / 32768.0

    result = model.transcribe(audio, language="en", fp16=False, verbose=False)
    text   = result["text"].strip()

    if not text:
        print("[voice] (nothing transcribed — try speaking louder or closer)")
    else:
        print(f"[voice] Got: '{text}'")
    return text


# ── Wake word ─────────────────────────────────────────────────────

def listen_for_wake() -> bool:
    """Record a short clip and check for the wake phrase."""
    audio = record_fixed(duration=3.0)
    text  = transcribe(audio).lower()
    return WAKE_PHRASE in text


# ── Full input pipeline ───────────────────────────────────────────

def record_challenge() -> str:
    """Record until silence, return full transcript."""
    audio = record_until_silence()
    return transcribe(audio)


# ── Speech output ─────────────────────────────────────────────────

_say_proc = None

def speak(text: str, slow: bool = False):
    """
    Speak text through laptop speaker.
    macOS: `say` command — clean quality, Ctrl+C interruptible.
    Other: pyttsx3 fallback.
    """
    global _say_proc
    print(f"[voice] 🔊 {text}")

    if _is_mac():
        try:
            voice = "Karen"     if slow else "Samantha"
            rate  = "155"       if slow else "190"
            _say_proc = subprocess.Popen(["say", "-v", voice, "-r", rate, text])
            _say_proc.wait()
            _say_proc = None
        except KeyboardInterrupt:
            if _say_proc:
                _say_proc.terminate()
                _say_proc = None
            raise
    else:
        pyttsx3 = _require("pyttsx3")
        engine  = pyttsx3.init()
        engine.setProperty("rate", 140 if slow else 170)
        engine.say(text)
        engine.runAndWait()
        engine.stop()


# ── Standalone test ───────────────────────────────────────────────

if __name__ == "__main__":
    preload()

    print("=" * 50)
    print("CubeBot voice pipeline — standalone test")
    print("=" * 50)

    mode = input(
        "\nTest mode:\n"
        "  1 — wake word detection\n"
        "  2 — record + transcribe\n"
        "  3 — TTS output (normal)\n"
        "  4 — TTS output (story/slow)\n"
        "Choose (1/2/3/4): "
    ).strip()

    if mode == "1":
        print(f"\nSay '{WAKE_PHRASE}' into your mic...")
        detected = listen_for_wake()
        print(f"\nResult: {'✅ Wake word detected!' if detected else '❌ Not detected.'}")

    elif mode == "2":
        print("\nSpeak your challenge. Pause when done.")
        text = record_challenge()
        print(f"\nFinal transcript: '{text}'")

    elif mode == "3":
        text = input("\nEnter text to speak: ")
        speak(text)
        print("Done.")

    elif mode == "4":
        text = input("\nEnter story text: ")
        speak(text, slow=True)
        print("Done.")

    else:
        print("Invalid choice.")
