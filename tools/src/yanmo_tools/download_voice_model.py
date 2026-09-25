"""
Script to download SenseVoice-Small INT8 model for YanMo IME (言墨输入法).
Model size: ~239MB INT8, tokens: ~315KB.
"""

import os
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
MODEL_DIR = BASE_DIR / "data" / "models" / "sense-voice"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_URL = "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/model.int8.onnx"
TOKENS_URL = "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt"

MODEL_FILE = MODEL_DIR / "model.int8.onnx"
TOKENS_FILE = MODEL_DIR / "tokens.txt"


def download_file(url: str, dest: Path):
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"File already exists: {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")
        return

    print(f"Downloading {dest.name} from {url}...")
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]
    urllib.request.install_opener(opener)

    def report(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size) if total_size > 0 else 0
        sys.stdout.write(f"\rDownloading {dest.name}: {percent}% ({count * block_size / 1024 / 1024:.1f} MB)")
        sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, reporthook=report)
    print(f"\nSaved to {dest}")


def main():
    print(f"Target directory: {MODEL_DIR}")
    download_file(TOKENS_URL, TOKENS_FILE)
    download_file(MODEL_URL, MODEL_FILE)
    print("SenseVoice-Small model files are ready!")


if __name__ == "__main__":
    main()
