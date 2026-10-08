import io

from PIL import Image


class ImageDecodeError(Exception):
    """Байты не являются читаемым изображением."""


def decode_image(image_bytes: bytes) -> Image.Image:
    if not image_bytes:
        raise ImageDecodeError("empty image")
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        return image.convert("RGB")
    except Exception as exc:
        raise ImageDecodeError("cannot read image") from exc
