"""Aggregate retrieval measures separately from explicit human answer scores."""
from collections import defaultdict
from statistics import mean

def summarize(records):
    groups=defaultdict(list)
    for record in records:
        key=record['strategy']+('_rerank' if record.get('rerank') else '')
        groups[key].append(record)
    result=[]
    for variant,rows in groups.items():
        summary={'variant':variant,'cases':len(rows)}
        for field in ['recall','mrr','ndcg']:
            values=[r['metrics'][field] for r in rows if r.get('metrics',{}).get(field) is not None]
            summary[field]=mean(values) if values else None
            summary[field+'_samples']=len(values)
        for field in ['retrieval_ms','reranker_ms','end_to_end_ms']:
            values=[r[field] for r in rows if field in r]
            summary[field]=mean(values) if values else None
        scores=[r['human_review']['score'] for r in rows if r.get('human_review')]
        summary['human_score']=mean(scores) if scores else None
        summary['human_reviewed']=len(scores)
        result.append(summary)
    return result
