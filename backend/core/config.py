from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    pg_addr: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_database: str = "xv6_rag"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_max_tokens: int | None = None
    llm_reasoning_effort: str | None = None
    judge_model: str | None = None
    embedding_model: str = "intfloat/multilingual-e5-small"
    reranker_model: str = "BAAI/bge-reranker-base"
    default_code_version: str = "dc9153fcb9c9b762dfaae9f586aecdaf04fb68fe"

    @field_validator("llm_max_tokens", mode="before")
    @classmethod
    def normalize_max_tokens(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, str):
            value = value.strip()
        number = int(value)
        return number if number > 0 else None

    @property
    def url(self):
        return URL.create(
            "postgresql+psycopg",
            username=self.pg_user,
            password=self.pg_password,
            host=self.pg_addr,
            port=self.pg_port,
            database=self.pg_database,
        )


settings = Settings()
