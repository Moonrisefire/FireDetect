from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import cv_router
from app.db.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FireWatch Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cv_router, prefix="/api")


@app.get("/")
def home():
    return {"status": "Работает", "docs": "Перейдите на /docs для тестирования"}
