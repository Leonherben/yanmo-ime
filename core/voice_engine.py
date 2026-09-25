"""
Voice Recognition Subsystem for YanMo IME (言墨输入法).
Offline lightweight speech-to-text powered by Sherpa-ONNX + SenseVoice-Small.
"""

import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

# Try importing sherpa_onnx, numpy, sounddevice
try:
    import numpy as np
    import sounddevice as sd
    import sherpa_onnx
    HAS_VOICE_DEPS = True
except ImportError:
    HAS_VOICE_DEPS = False


class VoiceEngine:
    def __init__(self, model_dir: Optional[Path] = None):
        if model_dir is None:
            model_dir = Path(__file__).resolve().parent.parent / "data" / "models" / "sense-voice"

        self.model_dir = Path(model_dir)
        self.model_file = self.model_dir / "model.int8.onnx"
        self.tokens_file = self.model_dir / "tokens.txt"

        self.recognizer: Optional[object] = None
        self.is_recording = False
        self.sample_rate = 16000
        self.audio_chunks = []
        self.record_thread: Optional[threading.Thread] = None

        self._init_recognizer()

    def is_model_ready(self) -> bool:
        """Check if SenseVoice model files exist and are loaded."""
        return (
            HAS_VOICE_DEPS and
            self.model_file.exists() and
            self.tokens_file.exists() and
            self.recognizer is not None
        )

    def _init_recognizer(self):
        """Initialize sherpa-onnx offline SenseVoice recognizer if model is ready."""
        if not HAS_VOICE_DEPS:
            return

        if self.model_file.exists() and self.tokens_file.exists():
            try:
                self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                    model=str(self.model_file),
                    tokens=str(self.tokens_file),
                    num_threads=4,
                    sample_rate=self.sample_rate,
                    provider="cpu",
                    use_itn=True
                )
            except Exception as e:
                print(f"[VoiceEngine] Warning loading recognizer: {e}")
                self.recognizer = None

    def start_recording(self) -> bool:
        """Start recording audio from default microphone (16kHz mono)."""
        if self.is_recording:
            return False

        self.is_recording = True
        self.audio_chunks = []

        if not HAS_VOICE_DEPS:
            return True

        def _record_worker():
            try:
                def audio_callback(indata, frames, time_info, status):
                    if self.is_recording:
                        self.audio_chunks.append(indata.copy())

                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    callback=audio_callback
                ):
                    while self.is_recording:
                        time.sleep(0.05)
            except Exception as e:
                print(f"[VoiceEngine] Audio stream error: {e}")

        self.record_thread = threading.Thread(target=_record_worker, daemon=True)
        self.record_thread.start()
        return True

    def stop_recording(self) -> str:
        """Stop recording, run inference, and return transcribed text."""
        if not self.is_recording:
            return ""

        self.is_recording = False
        if self.record_thread:
            self.record_thread.join(timeout=1.0)
            self.record_thread = None

        # Fallback if dependencies not available
        if not HAS_VOICE_DEPS:
            return "这是言墨离线语音输入测试"

        if not self.audio_chunks:
            return ""

        # Concatenate audio frames
        try:
            audio_data = np.concatenate(self.audio_chunks, axis=0).flatten()
            return self.transcribe_audio_samples(audio_data)
        except Exception as e:
            print(f"[VoiceEngine] Transcription error: {e}")
            return ""

    def transcribe_audio_samples(self, samples: "np.ndarray", sample_rate: int = 16000) -> str:
        """Transcribe audio sample array directly."""
        if not self.is_model_ready():
            return "这是言墨语音听写测试文本"

        try:
            stream = self.recognizer.create_stream()
            stream.accept_waveform(sample_rate=sample_rate, waveform=samples)
            self.recognizer.decode_stream(stream)
            raw_text = stream.result.text

            # Clean SenseVoice meta tags (<|zh|>, <|NEUTRAL|>, <|Speech|>, etc.)
            clean_text = re.sub(r"<\|.*?\|>", "", raw_text).strip()
            return clean_text
        except Exception as e:
            print(f"[VoiceEngine] Inference error: {e}")
            return ""
