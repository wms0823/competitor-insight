"""综合测评 Agent — 交叉验证四个维度的分析结果，生成最终决策报告。"""

import logging

from langchain_core.messages import SystemMessage

from src.config import settings
from src.observability import AgentMetrics
from src.state import ComparisonState

logger = logging.getLogger(__name__)

EVALUATOR_PROMPT = """\
你是资深技术选型顾问。综合以下四个维度的竞品分析，交叉验证、冲突检测，输出可操作的决策建议。

## 对比对象
- 产品A: {product_a}  |  产品B: {product_b}  |  品类: {category}

## 四维分析数据

### 功能维度
{feature_result}

### 价格维度
{pricing_result}

### 口碑维度
{sentiment_result}

### 场景维度
{scenario_result}

## 输出规范

**格式要求：**
- 使用标准 Markdown，不要用 `---` 分隔线
- 所有标题从 `##` 开始
- 表格必须对齐、数据真实（不要留空或填占位符）
- 语言简洁，面向业务决策者（非技术人员也可理解）
- 不要使用任何 HTML 注释标签
- 评分用「8/10」格式，不要用星星等符号

**必须包含以下板块（按顺序）：**

## 一、总评
用 2-3 句话说明两款产品的核心差异和选择导向。

## 二、各维度对比一览

用一张表格汇总四个维度的打分和一句话点评：

| 对比维度 | {product_a} | {product_b} | 一句话点评 |
|---------|------------|------------|-----------|
| 功能 | X/10 | Y/10 | ... |
| 价格 | X/10 | Y/10 | ... |
| 口碑 | X/10 | Y/10 | ... |
| 场景 | X/10 | Y/10 | ... |

## 三、交叉验证

- 数据最扎实的维度和原因
- 信息不足或不确定的地方
- 各维度结论是否一致

## 四、关键差异

分条列出两个产品最本质的 3-5 个不同点（功能定位、价格策略、目标用户、生态等），每条不超过 60 字。

## 五、冲突发现

如果各维度结论一致就写「各维度结论一致，未发现明显矛盾」；如果有矛盾（比如功能得分高但口碑差），说明可能的原因。

## 六、分场景推荐

| 用户画像 | 推荐 | 理由 |
|---------|------|------|
| 个人用户 | {product_a} 或 {product_b} | 一句话理由 |
| 小团队（2-10人） | {product_a} 或 {product_b} | 一句话理由 |
| 中型企业（10-100人） | {product_a} 或 {product_b} | 一句话理由 |
| 大型企业（100人以上） | {product_a} 或 {product_b} | 一句话理由 |

## 七、选型建议

按优先级列出 3-5 条决策建议，每条包含：在什么情况下选哪个产品、需要注意什么风险。用加粗标注产品名称。
"""

# 每维度最大输入字符数
DIM_TRIM_CHARS = 1500


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
    report = resp.content.replace("\r\n", "\n").strip()
    metrics.stop()

    logger.info(
        "Evaluator 评审完成 — %d 字 | %d ms",
        len(report), metrics.elapsed_ms,
    )

    existing = state.get("agent_metrics", {})
    existing["evaluator"] = metrics.to_dict()

    return {
        "final_report": report,
        "conflict_points": "",
        "agent_metrics": existing,
    }
