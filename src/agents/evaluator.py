"""综合测评 Agent — 交叉验证四个维度的分析结果，生成最终决策报告。"""

import logging
import re

from langchain_core.messages import SystemMessage

from src.config import settings
from src.observability import AgentMetrics
from src.state import ComparisonState

logger = logging.getLogger(__name__)

EVALUATOR_PROMPT = """\
你是资深技术选型顾问。请综合以下四个维度的竞品分析，进行交叉验证、冲突检测，并给出可操作的决策建议。

## 对比对象
- 产品A: {product_a}
- 产品B: {product_b}
- 品类: {category}

## 四维分析数据

### 功能维度
{feature_result}

### 价格维度
{pricing_result}

### 口碑维度
{sentiment_result}

### 场景维度
{scenario_result}

## 输出格式（严格按以下模板，用 `---` 分隔各板块）

### 总评
一句话结论。

---

### 交叉验证
- 数据最扎实的维度及原因
- 信息不足或存在推测的维度
- 各维度结论一致性判断

---

### 冲突点
矛盾结论及原因（无冲突则写"各维度结论一致，无明显冲突"）

---

### 综合评分
| 维度 | 权重 | {product_a} | {product_b} | 说明 |
|------|------|------------|------------|------|
| 功能 | 30% | X/10 | Y/10 | |
| 价格 | 25% | X/10 | Y/10 | |
| 口碑 | 25% | X/10 | Y/10 | |
| 场景 | 20% | X/10 | Y/10 | |
| **加权总分** | **100%** | **X.X** | **Y.Y** | |

---

### 分场景推荐
| 用户画像 | 推荐产品 | 核心理由 |
|----------|---------|---------|
| 个人/自由职业者 | | |
| 小团队（2-10人） | | |
| 中型企业（10-100人） | | |
| 大型企业（100+人） | | |

---

### 技术决策建议
3-5 条，每条含 **建议**、**适用条件**、**风险提示**。

---

<!--CONFLICTS-->
冲突摘要
<!--END_CONFLICTS-->
"""

# 每维度最大输入字符数
DIM_TRIM_CHARS = 1500


def _dedup_separators(text: str) -> str:
    """合并连续的 --- 分隔线，避免空白板块。"""
    # 将连续的 "---\n\n---" 合并为单个 "---"
    text = re.sub(r'(\n---\s*){2,}', '\n\n---\n\n', text)
    # 去除开头多余的 ---
    text = text.lstrip("\n")
    if text.startswith("---"):
        text = text[3:].lstrip("\n")
    return text


def evaluator_agent(state: ComparisonState) -> dict:
    """综合四个维度的分析结果，生成最终评审报告。"""
    a = state["product_a"]
    b = state["product_b"]
    cat = state.get("category", "通用")

    def _trim(text: str, max_chars: int = DIM_TRIM_CHARS) -> str:
        if not text:
            return "（该维度暂无分析结果）"
        text = text.strip()
        if len(text) <= max_chars:
            return text
        cut = text.rfind("\n", 0, max_chars)
        if cut > max_chars // 2:
            return text[:cut] + "\n...(已截断)"
        return text[:max_chars] + "\n...(已截断)"

    feature = _trim(state.get("feature_result", ""))
    pricing = _trim(state.get("pricing_result", ""))
    sentiment = _trim(state.get("sentiment_result", ""))
    scenario = _trim(state.get("scenario_result", ""))

    llm = settings.get_llm(temperature=0.1)
    prompt = EVALUATOR_PROMPT.format(
        product_a=a, product_b=b, category=cat,
        feature_result=feature,
        pricing_result=pricing,
        sentiment_result=sentiment,
        scenario_result=scenario,
    )

    metrics = AgentMetrics()
    metrics.start()

    logger.info("Evaluator 开始综合评审...")
    resp = llm.invoke([SystemMessage(content=prompt)])
    metrics.record_llm_call()
    report = resp.content.replace("\r\n", "\n")

    # ── 后处理：清理格式 ──
    report = _dedup_separators(report)

    # ── 解析冲突摘要 ──
    conflicts = ""
    if "<!--CONFLICTS-->" in report and "<!--END_CONFLICTS-->" in report:
        start = report.index("<!--CONFLICTS-->") + len("<!--CONFLICTS-->")
        end = report.index("<!--END_CONFLICTS-->")
        conflicts = report[start:end].strip()
        # 清理前缀
        prefix = report[: start - len("<!--CONFLICTS-->")].rstrip()
        while prefix.endswith("---"):
            prefix = prefix[:-3].rstrip("\n").rstrip()
        report = (
            prefix
            + "\n\n---\n\n### 冲突摘要\n\n" + conflicts + "\n"
            + report[end + len("<!--END_CONFLICTS-->"):].strip()
        )

    report = _dedup_separators(report)
    metrics.stop()

    logger.info(
        "Evaluator 评审完成 — %d 字 | %d ms",
        len(report), metrics.elapsed_ms,
    )

    existing = state.get("agent_metrics", {})
    existing["evaluator"] = metrics.to_dict()

    return {
        "final_report": report,
        "conflict_points": conflicts if conflicts else "无冲突",
        "agent_metrics": existing,
    }
