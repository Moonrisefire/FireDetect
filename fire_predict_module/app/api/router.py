from fastapi import APIRouter, HTTPException

dummy_router = APIRouter()

@dummy_router.post("/predict")
async def perform_predict():
    try:
        print("Hello? I think today is a beautiful weather!")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))