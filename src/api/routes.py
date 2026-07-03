from fastapi import APIRouter
from pydantic import BaseModel
from src.graph import build_graph
from src.config import settings

router = APIRouter()


class CompareRequest(BaseModel):
    product_a: str
    product_b: str
    category: str = "通用"


class CompareResponse(BaseModel):
    thread_id: str
    status: str
    report: str | None = None


@router.post("/compare", response_model=CompareResponse)
async def compare(req: CompareRequest):
    config = {
        "configurable": {
            "thread_id": f"cmp_{req.product_a[:10]}_vs_{req.product_b[:10]}"
        }
    }
    app = build_graph(settings.database_url)
    state = {
        "product_a": req.product_a,
        "product_b": req.product_b,
        "category": req.category,
        "completed_dims": [],
        "error_count": 0,
        "max_retries": 3,
    }
    result = app.invoke(state, config)
    return CompareResponse(
        thread_id=config["configurable"]["thread_id"],
        status="completed",
        report=result.get("final_report"),
    )
