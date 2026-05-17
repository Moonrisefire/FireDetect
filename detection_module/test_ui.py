import streamlit as st
import requests
from PIL import Image, ImageDraw
import io

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="FireWatch — Мониторинг пожаров", layout="wide")
st.title("Система детекции лесных пожаров (Computer Vision)")

col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("Управление")

    # Получаем список камер из БД
    try:
        cameras_response = requests.get(f"{API_URL}/cameras")
        if cameras_response.status_code == 200 and cameras_response.json():
            cameras = cameras_response.json()
            # Берем cam['name'] вместо cam['location']
            camera_options = {f"Камера №{cam['id']} ({cam.get('name', 'Лесной массив')})": cam['id'] for cam in cameras}
            selected_camera_text = st.selectbox("Выберите активную камеру:", list(camera_options.keys()))
            camera_id = camera_options[selected_camera_text]
        else:
            st.warning("⚠В базе данных пока нет камер. Используем тестовый ID = 1.")
            camera_id = 1
    except requests.exceptions.ConnectionError:
        st.error("Бэкенд-сервер не запущен! Сначала запусти uvicorn.")
        camera_id = 1

    uploaded_file = st.file_uploader("Загрузите снимок с камеры (JPG/PNG):", type=["jpg", "jpeg", "png"])
    start_analysis = st.button("Запустить анализ нейросетью", use_container_width=True)


with col1:
    st.subheader("Интерактивная карта мониторинга")

    # Рисуем карту мира на основе реальных координат из БД
    try:
        map_response = requests.get(f"{API_URL}/cameras")
        if map_response.status_code == 200 and map_response.json():
            cameras_data = map_response.json()
            map_points = [{"latitude": cam["latitude"], "longitude": cam["longitude"]} for cam in cameras_data]
            st.map(map_points)
        else:
            st.info("Нет данных для отображения карты.")
    except Exception:
        st.error("Не удалось загрузить координаты камер для карты.")

    st.write("---")

    if uploaded_file is not None:
        image = Image.open(uploaded_file)

        if start_analysis:
            with st.spinner("Нейросеть Hugging Face анализирует кадр..."):
                try:
                    uploaded_file.seek(0)
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

                    # Отправляем на роутер
                    response = requests.post(f"{API_URL}/cv/detect/{camera_id}", files=files)

                    if response.status_code == 200:
                        result = response.json()
                        is_fire = result.get("is_fire", False)
                        confidence = result.get("confidence", 0.0)
                        bboxes = result.get("bounding_boxes", [])

                        if is_fire:
                            st.error(f"ОБНАРУЖЕН ПОЖАР! Макс. уверенность: {confidence * 100:.1f}%")

                            draw = ImageDraw.Draw(image)
                            for box in bboxes:
                                x1, y1, x2, y2 = box["bbox"]
                                label = f"{box['class'].upper()} ({box['confidence'] * 100:.0f}%)"
                                color = "red" if box["class"] == "fire" else "orange"

                                draw.rectangle([x1, y1, x2, y2], outline=color, width=4)
                                draw.rectangle([x1, y1 - 20, x1 + 130, y1], fill=color)
                                draw.text((x1 + 5, y1 - 18), label, fill="white")
                        else:
                            st.success("Очагов возгорания и дыма не обнаружено. Всё спокойно.")

                        st.image(image, caption="Результат обработки кадра", use_container_width=True)
                    else:
                        st.error(f"Ошибка сервера: {response.json().get('detail', 'Неизвестная ошибка')}")
                except Exception as e:
                    st.error(f"Не удалось связаться с сервером: {e}")
        else:
            st.image(image, caption="Исходный кадр с камеры", use_container_width=True)
    else:
        st.info("Загрузите фотографию в правой панели, чтобы симулировать получение кадра с лесной камеры.")