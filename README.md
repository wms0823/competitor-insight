# 竞品深度对比分析系统

基于 **LangGraph Supervisor 多智能体架构**，输入两个产品名，4 个专业 Agent 并行从功能、价格、口碑、场景四个维度独立调研，Supervisor 汇总冲突点，生成决策建议。

## 技术栈

```
langgraph>=0.3.0 | langchain>=0.3.0 | langchain-openai
chromadb | redis | fastapi | uvicorn | sse-starlette
postgresql | docker | langsmith | deepseek (LLM)
```

## 快速开始

### 1. 启动基础设施

```bash
docker compose -f docker/docker-compose.yml up -d postgres redis
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 TAVILY_API_KEY
# DeepSeek 使用 OpenAI 兼容接口，ChatOpenAI 自动指向 https://api.deepseek.com
```

### 3. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

### 4. 启动服务

```bash
uvicorn src.api.main:app --reload --port 8080
```

### 5. 测试请求

```bash
curl -X POST http://localhost:8080/compare \
  -H "Content-Type: application/json" \
  -d '{"product_a":"Notion","product_b":"飞书文档","category":"文档协作工具"}'
```

### 6. 运行测试

```bash
pip install pytest && python -m pytest tests/ -v
```

## 项目结构

```
competitor-insight/
├── src/
│   ├── state.py          # 全局状态定义
│   ├── graph.py          # LangGraph 图构建 + 编译
│   ├── supervisor.py     # Supervisor 路由 Agent
│   ├── agents/
│   │   ├── feature.py    # 功能对比 Agent
│   │   ├── pricing.py    # 价格对比 Agent
│   │   ├── sentiment.py  # 口碑对比 Agent
│   │   └── scenario.py   # 场景对比 Agent
│   ├── tools/
│   │   ├── search.py     # 搜索工具
│   │   ├── scraper.py    # 网页抓取
│   │   └── rag.py        # 知识库检索
│   ├── api/
│   │   ├── main.py       # FastAPI 入口
│   │   └── routes.py     # 接口路由
│   └── config.py         # 配置管理
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile
├── tests/
│   └── test_graph.py
├── .env.example
├── pyproject.toml
└── README.md
```

## 架构说明

四个 Agent 不是串行，是 **Supervisor 轮询调度**——每轮选择一个未完成的维度派发，Agent 完成后回到 Supervisor 汇报结果，Supervisor 再选下一个。这保证了顺序可控，且每个 Agent 完成后 Supervisor 可以立即判断是否需要调整策略。

## API

### POST /compare

```json
{
  "product_a": "Notion",
  "product_b": "飞书文档",
  "category": "文档协作工具"
}
```

响应：

```json
{
  "thread_id": "cmp_Notion_vs_飞书文档",
  "status": "completed",
  "report": "# 竞品对比分析报告\n..."
}
```
