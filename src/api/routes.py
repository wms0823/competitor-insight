"""API 路由 — 竞品对比分析端点。"""

import asyncio
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config import settings
from src.graph import build_graph
from src.observability import set_trace_id

router = APIRouter(tags=["竞品对比"])

# 单次对比分析最大等待时间（秒）
ANALYSIS_TIMEOUT = 180


class CompareRequest(BaseModel):
    """竞品对比请求"""

    product_a: str = Field(
        ...,
        title="产品A",
        description="产品A的名称",
        examples=["Notion"],
        min_length=1,
        max_length=100,
    )
    product_b: str = Field(
        ...,
        title="产品B",
        description="产品B的名称",
        examples=["飞书文档"],
        min_length=1,
        max_length=100,
    )
    category: str = Field(
        "通用",
        title="品类",
        description="产品所属品类",
        examples=["文档协作工具"],
        max_length=50,
    )


class CompareResponse(BaseModel):
    """竞品对比响应"""

    trace_id: str = Field(
        ...,
        title="追踪ID",
        description="请求级链路追踪标识，可用于日志检索",
    )
    thread_id: str = Field(
        ...,
        title="对话ID",
        description="LangGraph 对话线程标识",
    )
    status: str = Field(
        ...,
        title="状态",
        description="completed / timeout / error",
    )
    report: str | None = Field(
        None,
        title="分析报告",
        description="最终对比分析报告（Markdown）",
    )
    metrics: dict | None = Field(
        None,
        title="性能指标",
        description="各 Agent 耗时、LLM 调用次数、工具调用统计",
    )
    error: str | None = Field(
        None,
        title="错误信息",
        description="失败时的错误描述",
    )


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="发起竞品对比分析",
    description=(
        "输入两个产品名称和品类，系统将自动从功能、价格、口碑、场景"
        "四个维度进行深度对比，并生成结构化分析报告。"
    ),
)
async def compare(req: CompareRequest):
    """发起竞品对比分析任务。"""
    # 生成唯一 ID（避免同名产品前缀碰撞）
    trace_id = uuid.uuid4().hex[:12]
    set_trace_id(trace_id)

    thread_id = f"cmp_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        app = build_graph(settings.database_url)
        state = {
            "product_a": req.product_a,
            "product_b": req.product_b,
            "category": req.category,
            "trace_id": trace_id,
            "agent_metrics": {},
            "completed_dims": [],
            "error_count": 0,
            "max_retries": 3,
        }
        result = await asyncio.wait_for(
            asyncio.to_thread(app.invoke, state, config),
            timeout=ANALYSIS_TIMEOUT,
        )
        return CompareResponse(
            trace_id=trace_id,
            thread_id=thread_id,
            status="completed",
            report=result.get("final_report"),
            metrics=result.get("agent_metrics"),
        )
    except asyncio.TimeoutError:
        return CompareResponse(
            trace_id=trace_id,
            thread_id=thread_id,
            status="timeout",
            error=f"分析超时（{ANALYSIS_TIMEOUT}秒），请稍后重试",
        )
    except Exception as e:
        return CompareResponse(
            trace_id=trace_id,
            thread_id=thread_id,
            status="error",
            error=f"{type(e).__name__}: {str(e)[:200]}",
        )
