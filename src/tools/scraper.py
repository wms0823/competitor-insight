from langchain_core.tools import tool
import trafilatura


@tool
def scrape_tool(url: str) -> str:
    """抓取网页正文，输入URL，返回纯文本内容。"""
    dl = trafilatura.fetch_url(url)
    text = trafilatura.extract(dl, include_links=False) if dl else None
    return text[:5000] if text else f"无法抓取: {url}"
