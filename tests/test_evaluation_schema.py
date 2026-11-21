import pytest
from pydantic import ValidationError

from backend.evaluation.schemas import Case, Experiment


def case():
    return Case(
        id="q1",
        question="question",
        reference_answer="answer",
        relevance={"chunk": 3},
        type="factual",
        annotation_status="complete",
    )


def test_duplicate_ids_cannot_bias_experiment_average():
    with pytest.raises(ValidationError):
        Experiment(cases=[case(), case()])


def test_candidate_budget_must_cover_top_k():
    with pytest.raises(ValidationError):
        Experiment(cases=[case()], top_k=10, candidates=5)


def test_invalid_relevance_grade_is_rejected():
    data = case().model_dump()
    data["relevance"] = {"chunk": 4}
    with pytest.raises(ValidationError):
        Case.model_validate(data)
