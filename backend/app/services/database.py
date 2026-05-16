from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./forest_guard.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Таблица истории детекций
class DetectionLog(Base):
    __tablename__ = "detection_logs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    is_fire = Column(Boolean)
    confidence = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Зависимость для получения сессии БД в роутерах
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
