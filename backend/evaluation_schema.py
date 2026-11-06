"""Shared API/CLI experiment schema and input validation."""

from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class Case(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1)
    relevance: dict[str, Annotated[int, Field(ge=0, le=3)]]
    type: str
    annotation_status: str = "pending"
    annotation_method: str = "unspecified"
    answer_criteria: str | None = None


class Experiment(BaseModel):
    cases: list[Case] = Field(min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=30)
    candidates: int = Field(default=20, ge=1, le=100)
    include_reranker: bool = False
    generate_answers: bool = False

    @model_validator(mode="after")
    def validate_design(self):
        if self.candidates < self.top_k:
            raise ValueError("候选数不能小于 Top K")
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("测试问题 ID 不能重复")
        return self
