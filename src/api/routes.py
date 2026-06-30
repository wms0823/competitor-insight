import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.graph import build_graph
from src.config import settings

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
    )
    product_b: str = Field(
        ...,
        title="产品B",
        description="产品B的名称",
        examples=["飞书文档"],
    )
    category: str = Field(
        "通用",
        title="品类",
        description="产品所属品类",
        examples=["文档协作工具"],
    )


class CompareResponse(BaseModel):
    """竞品对比响应"""

    thread_id: str = Field(
        ...,
        title="任务ID",
        description="对比任务的唯一标识",
        examples=["cmp_Notion_vs_飞书文档"],
    )
    status: str = Field(
        ...,
        title="状态",
        description="对比任务状态：completed/timeout/error",
        examples=["completed"],
    )
    report: str | None = Field(
        None,
        title="分析报告",
        description="最终对比分析报告（Markdown 格式）",
    )
    error: str | None = Field(
        None,
        title="错误信息",
        description="如果任务失败，返回错误描述",
    )


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="发起竞品对比分析",
    description="输入两个产品名称和品类，系统将自动从功能、价格、口碑、场景四个维度进行深度对比，并生成结构化分析报告。",
)
async def compare(req: CompareRequest):
    """发起竞品对比分析任务。

    - **product_a**: 第一个产品名称
    - **product_b**: 第二个产品名称
    - **category**: 产品所属品类（可选，默认为"通用"）
    """
    thread_id = f"cmp_{req.product_a[:10]}_vs_{req.product_b[:10]}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        app = build_graph(settings.database_url)
        state = {
            "product_a": req.product_a,
            "product_b": req.product_b,
            "category": req.category,
            "completed_dims": [],
            "error_count": 0,
            "max_retries": 3,
        }
        # 添加超时保护，防止长时间无响应
        result = await asyncio.wait_for(
            asyncio.to_thread(app.invoke, state, config),
            timeout=ANALYSIS_TIMEOUT,
        )
        return CompareResponse(
            thread_id=config["configurable"]["thread_id"],
            status="completed",
            report=result.get("final_report"),
        )
    except asyncio.TimeoutError:
        return CompareResponse(
            thread_id=thread_id,
            status="timeout",
            error=f"分析超时（{ANALYSIS_TIMEOUT}秒），请稍后重试或更换产品名称",
        )
    except Exception as e:
        return CompareResponse(
            thread_id=thread_id,
            status="error",
            error=f"分析失败: {type(e).__name__}: {str(e)[:200]}",
        )
