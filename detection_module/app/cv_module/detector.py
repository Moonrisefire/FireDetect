import torch
from ultralytics import YOLO

from .image_io import decode_image

original_load = torch.load

def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)

torch.load = patched_load

class WildfireDetector:
    def __init__(self, model_path: str = "ml/cv_module/weights/fire_model.pt"):
        self.model = YOLO(model_path)
        print(f"Модель распознавания пожаров успешно загружена из {model_path}")

    def analyze_image(self, image_bytes: bytes, conf_threshold: float = 0.35) -> dict:
        image = decode_image(image_bytes)
        results = self.model.predict(image, conf=conf_threshold, verbose=False)

        bounding_boxes = []
        max_confidence = 0.0

        for result in results:
            for box in result.boxes:
                coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                conf = round(box.conf[0].item(), 3)
                cls_id = int(box.cls[0].item())
                class_name = self.model.names[cls_id]

                if conf > max_confidence:
                    max_confidence = conf

                bounding_boxes.append({
                    "label": class_name,
                    "confidence": conf,
                    "x_min": round(coords[0], 1),
                    "y_min": round(coords[1], 1),
                    "x_max": round(coords[2], 1),
                    "y_max": round(coords[3], 1)
                })

        return {
            "is_fire": len(bounding_boxes) > 0,
            "confidence": max_confidence if bounding_boxes else 0.0,
            "bounding_boxes": bounding_boxes
        }