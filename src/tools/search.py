from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults


@tool
def search_tool(query: str) -> str:
    """搜索互联网，输入关键词，返回搜索结果。"""
    results = TavilySearchResults(max_results=3).invoke(query)
    return "\n\n".join(
        f"【{r['title']}】\n{r['content']}\n来源: {r['url']}"
        for r in results
    )
