from src.state import ComparisonState
from src.supervisor import supervisor_router


def test_route_to_first_pending():
    """测试：当无已完成维度时，路由到第一个待处理 Agent"""
    state = ComparisonState(
        product_a="Notion",
        product_b="飞书文档",
        category="文档工具",
        completed_dims=[],
        next_agent="feature",
        messages=[],
        feature_result=None,
        pricing_result=None,
        sentiment_result=None,
        scenario_result=None,
        final_report=None,
        conflict_points=None,
        error_count=0,
        max_retries=3,
    )
    assert supervisor_router(state) == "feature"


def test_route_to_end_when_all_done():
    """测试：当四个维度全部完成时，路由到 end"""
    state = ComparisonState(
        product_a="Notion",
        product_b="飞书文档",
        category="文档工具",
        completed_dims=["feature", "pricing", "sentiment", "scenario"],
        next_agent="end",
        messages=[],
        feature_result="done",
        pricing_result="done",
        sentiment_result="done",
        scenario_result="done",
        final_report=None,
        conflict_points=None,
        error_count=0,
        max_retries=3,
    )
    assert supervisor_router(state) == "end"


def test_route_to_end_when_max_retries():
    """测试：当错误次数超过最大重试时，路由到 end"""
    state = ComparisonState(
        product_a="Notion",
        product_b="飞书文档",
        category="文档工具",
        completed_dims=[],
        next_agent="feature",
        messages=[],
        feature_result=None,
        pricing_result=None,
        sentiment_result=None,
        scenario_result=None,
        final_report=None,
        conflict_points=None,
        error_count=3,
        max_retries=3,
    )
    assert supervisor_router(state) == "end"


def test_invalid_next_agent_returns_end():
    """测试：当 next_agent 为非法值时，返回 end"""
    state = ComparisonState(
        product_a="Notion",
        product_b="飞书文档",
        category="文档工具",
        completed_dims=[],
        next_agent="invalid_agent",
        messages=[],
        feature_result=None,
        pricing_result=None,
        sentiment_result=None,
        scenario_result=None,
        final_report=None,
        conflict_points=None,
        error_count=0,
        max_retries=3,
    )
    assert supervisor_router(state) == "end"
