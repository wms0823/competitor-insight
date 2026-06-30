from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres import PostgresSaver
from src.state import ComparisonState
from src.agents.feature import feature_agent
from src.agents.pricing import pricing_agent
from src.agents.sentiment import sentiment_agent
from src.agents.scenario import scenario_agent
from src.agents.evaluator import evaluator_agent

_compiled_graph = None
_cm = None  # 持有上下文管理器引用，防止连接被 GC 关闭


def build_graph(db_url: str):
    global _compiled_graph, _cm
    if _compiled_graph is not None:
        return _compiled_graph

    wf = StateGraph(ComparisonState)

    wf.add_node("feature", feature_agent)
    wf.add_node("pricing", pricing_agent)
    wf.add_node("sentiment", sentiment_agent)
    wf.add_node("scenario", scenario_agent)
    wf.add_node("evaluator", evaluator_agent)

    # 从 START 并行扇出到 4 个 Agent
    wf.add_edge(START, "feature")
    wf.add_edge(START, "pricing")
    wf.add_edge(START, "sentiment")
    wf.add_edge(START, "scenario")

    # 4 个 Agent 全部汇入综合测评节点
    wf.add_edge("feature", "evaluator")
    wf.add_edge("pricing", "evaluator")
    wf.add_edge("sentiment", "evaluator")
    wf.add_edge("scenario", "evaluator")

    wf.add_edge("evaluator", END)

    _cm = PostgresSaver.from_conn_string(db_url)
    checkpointer = _cm.__enter__()
    checkpointer.setup()
    _compiled_graph = wf.compile(checkpointer=checkpointer)
    return _compiled_graph
