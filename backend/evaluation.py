import math
def metrics(retrieved, relevance, k):
    ids=list(dict.fromkeys(retrieved))[:k]; relevant={x for x,g in relevance.items() if g>0}
    hits=[i+1 for i,x in enumerate(ids) if x in relevant]
    dcg=sum((2**relevance.get(x,0)-1)/math.log2(i+2) for i,x in enumerate(ids))
    ideal=sum((2**g-1)/math.log2(i+2) for i,g in enumerate(sorted(relevance.values(),reverse=True)[:k]))
    return {"recall":len(hits)/len(relevant) if relevant else None,"mrr":(1/hits[0] if hits else 0) if relevant else None,"ndcg":dcg/ideal if ideal else None}
