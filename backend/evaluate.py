"""Run retrieval ablations against a manually annotated JSONL dataset."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from .database import DB
from .evaluation import metrics
from .retrieval import search
from .config import settings


def run(dataset, output, k=5, candidates=20):
    cases = [json.loads(line) for line in Path(dataset).read_text(encoding='utf-8').splitlines() if line.strip()]
    if not cases or any(c.get('annotation_status') != 'complete' for c in cases):
        raise ValueError('Every test case must have annotation_status=complete before evaluation')
    records = []
    with DB() as db:
        for case in cases:
            for strategy, rerank in [('dense', False), ('hybrid', False), ('hybrid', True)]:
                found = search(db, case['question'], strategy, k, candidates, rerank)
                records.append({'case_id': case['id'], 'strategy': strategy, 'rerank': rerank,
                                'metrics': metrics([r['id'] for r in found['results']], case['relevance'], k),
                                **found})
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'k': k,
              'candidates': candidates, 'embedding_model': settings.embedding_model,
              'reranker_model': settings.reranker_model, 'scope': 'retrieval_only',
              'records': records}
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset')
    parser.add_argument('output')
    parser.add_argument('--k', type=int, default=5)
    parser.add_argument('--candidates', type=int, default=20)
    args = parser.parse_args()
    run(args.dataset, args.output, args.k, args.candidates)
