"""Request models shared by HTTP routers."""

from pydantic import BaseModel, Field, model_validator


class Query(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    strategy: str = Field(default="hybrid", pattern="^(dense|bm25|hybrid)$")
    top_k: int = Field(default=5, ge=1, le=30)
    candidates: int = Field(default=20, ge=1, le=100)
    rerank: bool = True
    rrf_k: int = Field(default=60, ge=1)
    version: str | None = None

    @model_validator(mode="after")
    def validate_candidates(self):
        if self.candidates < self.top_k:
            raise ValueError("候选数不能小于 Top K")
        return self


class Chat(Query):
    session_id: str
    rag: bool = True
    tools: bool = False
    tool_call_limit: int | None = Field(default=None, ge=1, le=100)


class Import(BaseModel):
    root: str
    commit: str | None = None
