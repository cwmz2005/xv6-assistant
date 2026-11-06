from backend.evaluation import metrics
from backend.retrieval import rrf, tokens
from backend.ingestion import split
def test_rrf():
    ids,s=rrf([["a","b"],["b","c"]]); assert ids[0]=="b"; assert abs(s["b"]-(1/62+1/61))<1e-10
def test_metrics():
    m=metrics(["x","a"],{"a":2,"b":1},2); assert m["recall"]==0.5; assert m["mrr"]==0.5; assert 0<m["ndcg"]<1
def test_split():
    parts=list(split("# A\nhello\n# B\nworld","a.md")); assert parts[1][1]["start_line"]==3
def test_identifiers(): assert "walkaddr" in tokens("walkaddr ????")
