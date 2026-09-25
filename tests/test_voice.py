import unittest
import numpy as np
from core.voice_engine import VoiceEngine


class TestVoiceEngine(unittest.TestCase):
    def setUp(self):
        self.voice_engine = VoiceEngine()

    def test_voice_engine_init(self):
        self.assertIsNotNone(self.voice_engine)
        self.assertFalse(self.voice_engine.is_recording)

    def test_record_lifecycle(self):
        # 1. Start recording
        started = self.voice_engine.start_recording()
        self.assertTrue(started)
        self.assertTrue(self.voice_engine.is_recording)

        # 2. Stop recording
        result = self.voice_engine.stop_recording()
        self.assertFalse(self.voice_engine.is_recording)
        self.assertIsInstance(result, str)

    def test_tag_cleaning(self):
        # Test SenseVoice tag stripping
        import re
        raw_output = "<|zh|><|NEUTRAL|><|Speech|><|woitn|>言墨输入法语音测试。"
        clean = re.sub(r"<\|.*?\|>", "", raw_output).strip()
        self.assertEqual(clean, "言墨输入法语音测试。")

    def test_synthetic_audio_inference(self):
        # Generate 0.5s of silent 16kHz mono audio
        sr = 16000
        samples = np.zeros(int(sr * 0.5), dtype=np.float32)
        text = self.voice_engine.transcribe_audio_samples(samples, sample_rate=sr)
        self.assertIsInstance(text, str)

    def test_engine_voice_integration(self):
        from core.engine import YanMoEngine
        engine = YanMoEngine()
        self.assertTrue(engine.voice_engine.is_model_ready())
        started = engine.start_voice_recording()
        self.assertTrue(started)
        text = engine.stop_voice_recording()
        self.assertIsInstance(text, str)


if __name__ == "__main__":
    unittest.main()

