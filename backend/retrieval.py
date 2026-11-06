import re, time
from functools import lru_cache
from sqlalchemy import select
from rank_bm25 import BM25Okapi
from .database import Chunk, RetrievalLog
from .ingestion import embedder
from .config import settings
def tokens(text): return re.findall(r"[a-z_][a-z_0-9]*|[\u4e00-\u9fff]",text.lower())
def rrf(rankings, k=60):
    scores={}
    for ranking in rankings:
        for rank, cid in enumerate(ranking,1): scores[cid]=scores.get(cid,0)+1/(k+rank)
    return sorted(scores, key=lambda cid: (-scores[cid],cid)),scores
@lru_cache(maxsize=1)
def reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(settings.reranker_model,device="cpu",max_length=512)
def search(db, query, strategy="hybrid", top_k=5, candidates=20, rerank=False, rrf_k=60):
    start=time.perf_counter(); rows=list(db.scalars(select(Chunk))); byid={r.id:r for r in rows}; scores={}; rankings=[]
    if not rows: return {"results":[],"retrieval_ms":0,"reranker_ms":0}
    if strategy in {"dense","hybrid"}:
        vector=embedder().embed_query("query: "+query)
        found=db.execute(select(Chunk.id,Chunk.embedding.cosine_distance(vector)).order_by(Chunk.embedding.cosine_distance(vector)).limit(candidates)).all()
        rankings.append([cid for cid,d in found])
        for cid,d in found: scores.setdefault(cid,{})["cosine_similarity"]=1-float(d)
    if strategy in {"bm25","hybrid"}:
        values=BM25Okapi([tokens(r.text) or ["_"] for r in rows]).get_scores(tokens(query))
        ordered=sorted(zip(rows,values),key=lambda x:-x[1])[:candidates]; rankings.append([r.id for r,s in ordered])
        for r,s in ordered: scores.setdefault(r.id,{})["bm25"]=float(s)
    ids,fused=rrf(rankings,rrf_k)
    if strategy=="hybrid":
        for cid,s in fused.items(): scores[cid]["rrf"]=s
    ids=ids[:candidates]; recall_ms=(time.perf_counter()-start)*1000; t=time.perf_counter()
    if rerank and ids:
        values=reranker().predict([(query,byid[cid].text) for cid in ids])
        for cid,s in zip(ids,values): scores[cid]["cross_encoder"]=float(s)
        ids.sort(key=lambda cid:-scores[cid]["cross_encoder"])
    result={"results":[{"id":cid,"text":byid[cid].text,"location":byid[cid].location,"scores":scores[cid],"rank":i+1} for i,cid in enumerate(ids[:top_k])],"retrieval_ms":recall_ms,"reranker_ms":(time.perf_counter()-t)*1000}
    db.add(RetrievalLog(payload={"query":query,"strategy":strategy,"candidates":candidates,"top_k":top_k,"rerank":rerank,"rrf_k":rrf_k,**result})); db.commit(); return result
