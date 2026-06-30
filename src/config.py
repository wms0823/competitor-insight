import os
from pydantic_settings import BaseSettings
from langchain_openai import ChatOpenAI


class Settings(BaseSettings):
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
    )
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://agent:agent123@localhost:5432/competitor",
    )
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
        )


settings = Settings()
if settings.langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = "competitor-insight"
