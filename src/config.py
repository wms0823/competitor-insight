import os
from pydantic_settings import BaseSettings
from langchain_openai import ChatOpenAI


def _build_database_url() -> str:
    """构建数据库连接字符串，优先使用 Railway 注入的独立变量。"""
    db_url = os.getenv("DATABASE_URL", "")
    if db_url and "localhost" not in db_url:
        return db_url

    # Railway 用 PGHOST/PGPORT 等独立变量注入 PostgreSQL
    pg_host = os.getenv("PGHOST", "")
    if pg_host:
        pg_user = os.getenv("PGUSER", "postgres")
        pg_password = os.getenv("PGPASSWORD", "")
        pg_port = os.getenv("PGPORT", "5432")
        pg_db = os.getenv("PGDATABASE", "railway")
        return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

    # 最后回退到 Railway 内部 DNS 格式
    if db_url:
        return db_url
    return "postgresql://agent:agent123@localhost:5432/competitor"


class Settings(BaseSettings):
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
    )
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    database_url: str = _build_database_url()
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")

    class Config:
        env_file = ".env"

    def get_llm(self, temperature: float = 0) -> ChatOpenAI:
        """获取 DeepSeek LLM 实例（OpenAI 兼容接口）。"""
        return ChatOpenAI(
            model=self.llm_model,
            temperature=temperature,
            api_key=self.deepseek_api_key,
            base_url=self.deepseek_base_url,
            request_timeout=60,
            max_retries=2,
        )


settings = Settings()
if settings.langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = "competitor-insight"