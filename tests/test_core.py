from backend.evaluation import metrics
from backend.ingestion import split
from backend.retrieval import rrf, tokens


def test_rrf():
    ids, s = rrf([["a", "b"], ["b", "c"]])
    assert ids[0] == "b"
    assert abs(s["b"] - (1 / 62 + 1 / 61)) < 1e-10


def test_metrics():
    m = metrics(["x", "a"], {"a": 2, "b": 1}, 2)
    assert m["recall"] == 0.5
    assert m["mrr"] == 0.5
    assert 0 < m["ndcg"] < 1


def test_split():
    parts = list(split("# A\nhello\n# B\nworld", "a.md"))
    assert parts[1][1]["start_line"] == 3


def test_identifiers():
    assert "walkaddr" in tokens("walkaddr 如何调用")


def test_rrf_does_not_double_count_duplicate_ids():
    ids, scores = rrf([["a", "a", "b"]])
    assert ids == ["a", "b"]
    assert scores["a"] == 1 / 61
    assert scores["b"] == 1 / 62


def test_out_of_scope_ranking_metrics_are_not_applicable():
    assert metrics(["unrelated"], {}, 5) == {"recall": None, "mrr": None, "ndcg": None}
