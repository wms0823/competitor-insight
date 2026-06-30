from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.api.routes import router

app = FastAPI(
    title="竞品深度对比分析系统",
    description="基于 LangGraph Supervisor 多智能体架构，输入两个产品名称，四个专业 Agent 并行从**功能**、**价格**、**口碑**、**场景**四个维度独立调研，Supervisor 汇总冲突点并生成决策建议。",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "竞品对比",
            "description": "发起竞品对比分析任务，获取多维度对比报告。",
        },
    ],
)

# 静态文件
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router)


@app.get("/", tags=["页面"])
async def index():
    """返回竞品对比分析系统首页"""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/health", tags=["系统"])
async def health():
    """健康检查端点"""
    return {"status": "ok", "version": "0.1.0"}
