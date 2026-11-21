from backend.evaluation.summary import summarize


def test_human_scores_are_never_inferred_from_retrieval():
    rows = [
        {
            "strategy": "dense",
            "metrics": {"recall": 1, "mrr": 1, "ndcg": 1},
            "retrieval_ms": 10,
        }
    ]
    s = summarize(rows)[0]
    assert s["human_score"] is None and s["human_reviewed"] == 0
    rows[0]["human_review"] = {"score": 0.5}
    assert summarize(rows)[0]["human_score"] == 0.5


def test_missing_relevance_is_excluded_from_recall_mean():
    s = summarize(
        [
            {"strategy": "dense", "metrics": {"recall": None}},
            {"strategy": "dense", "metrics": {"recall": 0.5}},
        ]
    )[0]
    assert s["recall"] == 0.5 and s["recall_samples"] == 1
