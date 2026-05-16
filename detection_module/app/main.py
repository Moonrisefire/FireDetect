from fastapi import FastAPI
from .api.router import cv_router
from .db.database import engine, Base

# Initialize local database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FireWatch Detection API")
app.include_router(cv_router, prefix="/api")

@app.get("/")
def home():
    return {"status": "OK", "message": "Detection module is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
