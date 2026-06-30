import os
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults
from src.config import settings


def _ensure_env_key():
    """确保 TAVILY_API_KEY 已写入环境变量（langchain_community 从 os.environ 读取）。"""
    if not os.getenv("TAVILY_API_KEY") and settings.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key


@tool
def search_tool(query: str) -> str:
    """搜索互联网，输入关键词，返回搜索结果。"""
    _ensure_env_key()
    results = TavilySearchResults(max_results=3).invoke(query)
    return "\n\n".join(
        f"【{r['title']}】\n{r['content']}\n来源: {r['url']}"
        for r in results
    )
