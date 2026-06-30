from fastapi import APIRouter
from pydantic import BaseModel, Field
from src.graph import build_graph
from src.config import settings

router = APIRouter(tags=["竞品对比"])


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
        description="对比任务状态：completed 表示已完成",
        examples=["completed"],
    )
    report: str | None = Field(
        None,
        title="分析报告",
        description="最终对比分析报告（Markdown 格式）",
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
