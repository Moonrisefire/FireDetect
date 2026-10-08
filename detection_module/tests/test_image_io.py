import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "cv_module" / "image_io.py"
spec = importlib.util.spec_from_file_location("fire_detect_image_io", MODULE_PATH)
image_io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_io)


def test_broken_bytes_are_not_a_quiet_image():
    with pytest.raises(image_io.ImageDecodeError):
        image_io.decode_image(b"this is not an image")


def test_empty_upload_is_rejected():
    with pytest.raises(image_io.ImageDecodeError):
        image_io.decode_image(b"")
