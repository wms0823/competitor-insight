"""网页抓取工具 — 供 ReAct Agent 调用的网页正文提取能力。"""

import logging

import trafilatura
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

MAX_CHARS = 2000


@tool
def scrape_tool(url: str) -> str:
    """抓取指定 URL 的网页正文内容。输入完整的网页链接（含 https://），返回提取的纯文本正文。适用于获取产品官网详情、深度评测文章等。"""
    logger.info("抓取网页: %s", url[:120])

    try:
        dl = trafilatura.fetch_url(url)
        if dl is None:
            return f"无法访问该网页: {url}（网站可能屏蔽了抓取或链接无效）"

        text = trafilatura.extract(dl, include_links=False)
        if not text:
            return f"网页内容提取失败: {url}（页面可能为空或为纯动态内容）"

        logger.info("抓取成功，原文 %d 字符", len(text))
        if len(text) <= MAX_CHARS:
            return text
        # 在换行处截断
        cut = text.rfind("\n", 0, MAX_CHARS)
        if cut > MAX_CHARS // 2:
            return text[:cut] + "\n...(内容过长，已截断)"
        return text[:MAX_CHARS] + "\n...(内容过长，已截断)"

    except Exception as exc:
        logger.error("抓取失败 %s: %s", url[:80], exc)
        return f"抓取失败（{type(exc).__name__}）: {str(exc)[:200]}"
