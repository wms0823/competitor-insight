import json
import logging
import traceback
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import settings
from src.graph import build_graph

logger = logging.getLogger(__name__)
router = APIRouter()


class CompareRequest(BaseModel):
    product_a: str
    product_b: str
    category: str = "通用"
    mode: str = "standard"  # "fast" | "standard" | "deep"


class CompareResponse(BaseModel):
    thread_id: str
    status: str
    report: str | None = None


# ── 普通接口（一次性返回） ──

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
        "mode": req.mode,
        "completed_dims": [],
        "progress": [],
        "error_count": 0,
        "max_retries": 3,
    }
    result = app.invoke(state, config)
    return CompareResponse(
        thread_id=config["configurable"]["thread_id"],
        status="completed",
        report=result.get("final_report"),
    )


# ── SSE 流式接口（实时进度推送） ──

async def _stream_compare(product_a: str, product_b: str, category: str, mode: str):
    """SSE 事件生成器：用 astream 实时推送每个节点的执行进度。"""
    thread_id = f"cmp_{product_a[:10]}_vs_{product_b[:10]}_{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}
    app = build_graph(settings.database_url)
    state = {
        "product_a": product_a,
        "product_b": product_b,
        "category": category,
        "mode": mode,
        "completed_dims": [],
        "progress": [],
        "error_count": 0,
        "max_retries": 3,
    }

    yield _sse("connected", {"thread_id": thread_id, "mode": mode})

    try:
        async for chunk in app.astream(state, config):
            node_name = next(iter(chunk.keys()), None) if chunk else None
            node_state = chunk.get(node_name, {}) if node_name else {}

            # ── 提取进度消息 ──
            progress = node_state.get("progress", [])
            for msg in progress:
                yield _sse("progress", {"message": msg, "agent": node_name})

            # ── 节点完成事件 ──
            if node_name in ("feature", "pricing", "sentiment", "scenario"):
                has_result = bool(node_state.get(f"{node_name}_result"))
                yield _sse(
                    "agent_done",
                    {"agent": node_name, "has_result": has_result},
                )
            elif node_name == "evaluator":
                report = node_state.get("final_report", "")
                yield _sse("evaluator_done", {"report_length": len(report)})
                yield _sse("report", {"report": report})

        yield _sse("done", {"thread_id": thread_id})

    except Exception as exc:
        logger.error("SSE 流异常: %s\n%s", exc, traceback.format_exc())
        yield _sse("error", {"message": str(exc)[:500]})


def _sse(event: str, data: dict) -> str:
    """构建一条 SSE 消息。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/compare/stream")
async def compare_stream(req: CompareRequest):
    """流式竞品对比分析：通过 SSE 实时推送进度。"""
    return StreamingResponse(
        _stream_compare(
            product_a=req.product_a,
            product_b=req.product_b,
            category=req.category,
            mode=req.mode,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
