from .app.db.database import SessionLocal, engine
from .app.db import models


def seed_cameras():
    db = SessionLocal()
    try:
        if db.query(models.Camera).count() > 0:
            print("База данных уже содержит камеры. Пропускаем.")
            return

        print("Наполнение базы данных тестовыми камерами по всему миру...")

        # Используем строго твои поля: name и zone_id
        test_cameras = [
            models.Camera(name="Тайга, Сибирь (Россия)", zone_id=1, latitude=56.5000, longitude=105.0000,
                          is_active=True),
            models.Camera(name="Национальный парк Йосемити (США)", zone_id=1, latitude=37.8651, longitude=-119.5383,
                          is_active=True),
            models.Camera(name="Леса Амазонки (Бразилия)", zone_id=1, latitude=-3.4653, longitude=-62.2159,
                          is_active=True),
            models.Camera(name="Леса Британской Колумбии (Канада)", zone_id=1, latitude=53.7267, longitude=-127.6476,
                          is_active=True),
            models.Camera(name="Эвкалиптовые леса (Австралия)", zone_id=1, latitude=-33.8688, longitude=151.2093,
                          is_active=True),
            models.Camera(name="Шварцвальд (Германия)", zone_id=1, latitude=48.0000, longitude=8.2500, is_active=True),
            models.Camera(name="Подмосковное лесничество (Россия)", zone_id=1, latitude=55.7558, longitude=37.6173,
                          is_active=True),
            models.Camera(name="Национальный парк Крюгер (ЮАР)", zone_id=1, latitude=-23.9884, longitude=31.5547,
                          is_active=True)
        ]

        db.add_all(test_cameras)
        db.commit()
        print("Успешно добавлено 8 тестовых камер с правильными полями!")
    except Exception as e:
        print(f"Ошибка при наполнении БД: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    models.Base.metadata.create_all(bind=engine)
    seed_cameras()