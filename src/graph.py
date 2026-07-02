"""竞品对比分析图 — 并行扇出 + ReAct 循环 + 综合评审。

图结构:
    START
      ├──> feature   (ReAct: 搜索 ↔ 抓取 → 功能对比)
      ├──> pricing   (ReAct: 搜索 ↔ 抓取 → 价格对比)
      ├──> sentiment (ReAct: 搜索 ↔ 抓取 → 口碑对比)
      └──> scenario  (ReAct: 搜索 ↔ 抓取 → 场景对比)
      |       │
      └───────┼──────> evaluator (综合评审 → 最终报告)
              └──────> END

每个维度 Agent 内部运行 ReAct 循环:
  LLM ↔ [search_tool, scrape_tool] → 多轮迭代 → 结构化结果
"""

import logging
import socket
import urllib.parse

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph

from src.agents.evaluator import evaluator_agent
from src.agents.feature import feature_agent
from src.agents.pricing import pricing_agent
from src.agents.scenario import scenario_agent
from src.agents.sentiment import sentiment_agent
from src.state import ComparisonState

logger = logging.getLogger(__name__)

_compiled_graph = None
_cm = None  # 持有 PostgresSaver 上下文管理器引用，防止连接被 GC 关闭

# PostgreSQL TCP 连接预检超时（秒）
_PG_CONNECT_TIMEOUT = 3


def _pg_port_is_open(db_url: str) -> bool:
    """快速 TCP 预检：PostgreSQL 端口是否可达。"""
    try:
        parsed = urllib.parse.urlparse(db_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        sock = socket.create_connection((host, port), timeout=_PG_CONNECT_TIMEOUT)
        sock.close()
        return True
    except Exception:
        return False


def _create_checkpointer(db_url: str):
    """创建 checkpointer，PostgreSQL 不可用时回退到内存模式。"""
    global _cm

    # 快速预检：端口不通则直接跳过，避免 TCP 长时间阻塞
    if not _pg_port_is_open(db_url):
        logger.info("PostgreSQL 端口不可达，使用 MemorySaver（内存模式）")
        return MemorySaver()

    # 尝试 PostgreSQL（连接串追加超时参数）
    try:
        sep = "&" if "?" in db_url else "?"
        db_url_with_timeout = f"{db_url}{sep}connect_timeout={_PG_CONNECT_TIMEOUT}"
        logger.info("尝试连接 PostgreSQL: %s", db_url.split("@")[-1] if "@" in db_url else db_url)
        _cm = PostgresSaver.from_conn_string(db_url_with_timeout)
        checkpointer = _cm.__enter__()
        checkpointer.setup()
        logger.info("✓ 使用 PostgreSQL checkpointer（支持对话持久化）")
        return checkpointer
    except Exception as exc:
        logger.warning("PostgreSQL 不可用 (%s)，回退到 MemorySaver", str(exc)[:100])
        _cm = None
        logger.info("✓ 使用 MemorySaver（内存模式，重启后历史记录丢失）")
        return MemorySaver()


def build_graph(db_url: str):
    """构建并编译 LangGraph 竞品对比分析图（单例模式）。

    首次调用时尝试 PostgreSQL checkpointer，
    不可用时自动回退到内存模式。
    """
    global _compiled_graph, _cm
    if _compiled_graph is not None:
        return _compiled_graph

    logger.info("构建竞品对比分析图...")

    wf = StateGraph(ComparisonState)

    # ── 注册节点 ──
    wf.add_node("feature", feature_agent)
    wf.add_node("pricing", pricing_agent)
    wf.add_node("sentiment", sentiment_agent)
    wf.add_node("scenario", scenario_agent)
    wf.add_node("evaluator", evaluator_agent)

    # ── 并行扇出：START → 四个维度 Agent ──
    wf.add_edge(START, "feature")
    wf.add_edge(START, "pricing")
    wf.add_edge(START, "sentiment")
    wf.add_edge(START, "scenario")

    # ── 汇聚：四个维度 Agent → evaluator ──
    wf.add_edge("feature", "evaluator")
    wf.add_edge("pricing", "evaluator")
    wf.add_edge("sentiment", "evaluator")
    wf.add_edge("scenario", "evaluator")

    # ── 结束 ──
    wf.add_edge("evaluator", END)

    # ── Checkpointer（PostgreSQL 优先，不可用时内存模式） ──
    checkpointer = _create_checkpointer(db_url)
    _compiled_graph = wf.compile(checkpointer=checkpointer)
    logger.info("竞品对比分析图编译完成")
    return _compiled_graph
