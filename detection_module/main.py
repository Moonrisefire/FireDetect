from fastapi import FastAPI
from app.api.router import cv_router
from app.db.database import engine, Base

# Initialize local database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FireWatch Detection API")

app.include_router(cv_router, prefix="/api")

@app.get("/")
def home():
    return {"status": "Работает", "docs": "Перейдите на /docs для тестирования"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
