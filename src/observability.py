"""可观测性基础设施 — trace_id 传播、Agent 耗时、工具调用统计。

用法:
    from src.observability import set_trace_id, get_trace_id, AgentMetrics, TraceContextFilter

    # API 层：每个请求生成 trace_id
    set_trace_id("abc123")

    # Agent 层：记录指标
    metrics = AgentMetrics()
    metrics.start()
    # ... work ...
    metrics.record_llm_call()
    metrics.record_tool_call("search_tool")
    metrics.stop()
    # metrics.to_dict() → {"elapsed_ms": 1234, "llm_calls": 2, ...}
"""

import contextvars
import logging
import time
from dataclasses import dataclass, field

# ── trace_id 上下文变量（自动跨线程/协程传播） ──
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default="-",
)


def set_trace_id(trace_id: str) -> None:
    """设置当前请求的 trace_id。"""
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """获取当前请求的 trace_id。"""
    return _trace_id_var.get()


# ── 日志过滤器：自动向每条日志注入 trace_id ──
class TraceContextFilter(logging.Filter):
    """注入 trace_id 到 LogRecord，配合 format 使用。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


# ── 防御性 Formatter：子线程中 contextvars 可能丢失，兜底处理 ──
class TraceFormatter(logging.Formatter):
    """与 TraceContextFilter 配合，缺失 trace_id 时回退为 '-'。"""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return super().format(record)


# ── Agent 指标采集器 ──
@dataclass
class AgentMetrics:
    """单个 Agent 的运行指标。"""

    started_at: float = 0.0
    finished_at: float = 0.0
    llm_calls: int = 0
    tool_calls: int = 0
    tools_used: dict = field(default_factory=dict)  # {"search_tool": 3, "scrape_tool": 1}

    def start(self) -> None:
        self.started_at = time.monotonic()

    def stop(self) -> None:
        self.finished_at = time.monotonic()

    def record_llm_call(self) -> None:
        self.llm_calls += 1

    def record_tool_call(self, tool_name: str) -> None:
        self.tool_calls += 1
        self.tools_used[tool_name] = self.tools_used.get(tool_name, 0) + 1

    @property
    def elapsed_ms(self) -> int:
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at) * 1000)
        return 0

    def to_dict(self) -> dict:
        return {
            "elapsed_ms": self.elapsed_ms,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "tools_used": self.tools_used,
        }
