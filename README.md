<div align="center">

# 竞品深度对比分析系统

**基于 LangGraph 多智能体架构的 AI 竞品分析引擎**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.3+-purple?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Railway](https://img.shields.io/badge/Railway-一键部署-0B0D0E?logo=railway&logoColor=white)](https://railway.app)

[快速开始](#快速部署试用) · [项目架构](#项目架构) · [API 文档](#api-使用) · [本地运行](#本地运行)

</div>

---

输入两个产品名称，**4 个专业 Agent 并行从功能、价格、口碑、场景四个维度独立调研**，再由综合测评 Agent 交叉验证、冲突检测、加权评分，最终生成**分场景的技术选型建议**。

---

## 快速部署试用

**点击下方按钮，1 分钟部署到 Railway，即可生成可在浏览器直接访问的在线 URL。**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/your-username/competitor-insight)

> 部署前需要准备两个免费 API Key（见下方说明）。

### 准备工作：获取 API Key

| 服务 | 用途 | 获取地址 | 是否免费 |
|------|------|----------|---------|
| **DeepSeek** | LLM 分析引擎 | https://platform.deepseek.com | 注册送 500 万 tokens |
| **Tavily** | 搜索引擎 | https://tavily.com | 每月 1000 次免费查询 |

### Railway 部署步骤

1. **Fork 或 Push** 代码到自己的 GitHub 仓库
2. **点击上方「Deploy on Railway」按钮**，或前往 [Railway](https://railway.app) → New Project → Deploy from GitHub repo
3. 在 Railway  Dashboard 中按顺序操作：

   **① 添加 PostgreSQL 数据库**
   ```
   New → Database → PostgreSQL
   ```
   Railway 会自动创建数据库并生成 `DATABASE_URL` 环境变量。

   **② 添加 Redis**
   ```
   New → Database → Redis
   ```
   Railway 会自动创建并生成 `REDIS_URL` 环境变量。

   **③ 设置环境变量**
   在项目 Variables 中添加：
   ```
   DEEPSEEK_API_KEY = <你的 DeepSeek API Key>
   TAVILY_API_KEY   = <你的 Tavily API Key>
   ```

4. **部署完成**后，Railway 会自动分配一个 `https://your-app.railway.app` 的公开 URL

> 面试官访问该 URL 即可以直接使用完整的竞品对比分析系统。

---

## 本地面试演示

也可以在本机给面试官演示，一行命令启动：

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 TAVILY_API_KEY

# 2. 安装依赖
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -e .

# 3. 启动服务
uvicorn src.api.main:app --reload --port 8080
```

浏览器打开 `http://localhost:8080` 即可使用。

---

## 项目架构

### 多智能体并行分析流程

```
START
  ├──> feature   ──┐
  ├──> pricing   ──┤
  ├──> sentiment ──┤
  └──> scenario  ──┘
                    └──> evaluator ──> END
```

**4 个专业 Agent** 并行搜索 + LLM 分析，结果全部汇入 **综合测评 Agent（evaluator）** 进行：

| 步骤 | 说明 |
|------|------|
| **交叉验证** | 检查各维度结论是否有事实支撑，逻辑是否一致 |
| **冲突检测** | 找出矛盾结论并分析原因（功能强但口碑差？价格低但场景受限？） |
| **加权综合评分** | 功能 30% + 价格 25% + 口碑 25% + 场景 20% |
| **分场景选型** | 针对个人/小团队、中型企业、大型企业分别推荐 |
| **最终建议** | 3-5 条可操作决策建议，含适用条件和风险提示 |

### 目录结构

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
│   │   ├── scenario.py   # 场景对比 Agent
│   │   ├── evaluator.py  # 综合测评 Agent（核心）
│   │   └── summarize.py  # 已被 evaluator 替代
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
├── static/
│   └── index.html        # 前端页面
├── tests/
│   └── test_graph.py
├── railway.json          # Railway 部署配置
├── Procfile              # Heroku/Railway 进程定义
├── pyproject.toml        # 项目依赖
├── .env.example          # 环境变量模板
└── README.md
```

---

## API 使用

### POST /compare

发起对比分析请求：

```bash
curl -X POST http://localhost:8080/compare \
  -H "Content-Type: application/json" \
  -d '{"product_a":"Notion","product_b":"飞书文档","category":"文档协作工具"}'
```

**请求参数：**

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `product_a` | string | 产品 A 名称 | Notion |
| `product_b` | string | 产品 B 名称 | 飞书文档 |
| `category` | string | 产品品类（可选） | 文档协作工具 |

**响应示例：**

```json
{
  "thread_id": "cmp_Notion_vs_飞书文档",
  "status": "completed",
  "report": "# 竞品对比分析报告\n..."
}
```

返回的 `report` 是 Markdown 格式的结构化分析报告，包含四个维度对比、综合评分和分场景选型建议。

---

## 技术栈

| 类别 | 技术 |
|------|------|
| AI 框架 | LangGraph 0.3+, LangChain 0.3+ |
| LLM | DeepSeek Chat (OpenAI 兼容接口) |
| 搜索 | Tavily Search API |
| Web 框架 | FastAPI + Uvicorn |
| 前端 | 纯 HTML/CSS/JS（零依赖） |
| 数据库 | PostgreSQL (pgvector) + Redis |
| 容器化 | Docker + Docker Compose |
| 部署 | Railway / Heroku / 自托管 |

---

## 本地开发

```bash
# 启动基础设施（PostgreSQL + Redis）
docker compose -f docker/docker-compose.yml up -d postgres redis

# 安装项目依赖
pip install -e .

# 运行测试
python -m pytest tests/ -v

# 启动开发服务器
uvicorn src.api.main:app --reload --port 8080
```

---

## License

[MIT](LICENSE)