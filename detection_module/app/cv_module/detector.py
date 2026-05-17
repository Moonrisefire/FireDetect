import io
from PIL import Image
from ultralytics import YOLO


class WildfireDetector:
    def __init__(self, model_path: str = "ml/cv_module/weights/fire_model.pt"):
        self.model = YOLO(model_path)
        print(f"Модель распознавания пожаров успешно загружена из {model_path}")

    def analyze_image(self, image_bytes: bytes, conf_threshold: float = 0.35) -> dict:
        try:
            # Превращаем байты из интернета в картинку
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Прогоняем через нейросеть
            results = self.model.predict(image, conf=conf_threshold, verbose=False)

            bounding_boxes = []
            max_confidence = 0.0

            for result in results:
                for box in result.boxes:
                    coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    conf = round(box.conf[0].item(), 3)
                    cls_id = int(box.cls[0].item())
                    class_name = self.model.names[cls_id]  # 'fire' или 'smoke'

                    if conf > max_confidence:
                        max_confidence = conf

                    bounding_boxes.append({
                        "class": class_name,
                        "confidence": conf,
                        "bbox": [round(c, 1) for c in coords]
                    })

            return {
                "is_fire": len(bounding_boxes) > 0,
                "confidence": max_confidence if bounding_boxes else 0.0,
                "bounding_boxes": bounding_boxes
            }
        except Exception as e:
            print(f"❌ Ошибка анализа изображения: {e}")
            return {"is_fire": False, "confidence": 0.0, "bounding_boxes": []}