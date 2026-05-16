from fastapi import APIRouter
from ..schemas.schemas import RiskResponse, RiskRequest

risk_router = APIRouter()

@risk_router.post("/evaluate", response_model=RiskResponse)
def evaluate(data: RiskRequest):
    # тут делать запрос к Метео-API и затем прогонять по алгоритму   
    return {
        "risk_level": "High",
        "score": 0.85,
        "temp": 32.5,
        "humidity": 15.0
    }
