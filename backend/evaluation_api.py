"""Explicit human annotations and reproducible retrieval experiments."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from .database import DB, Chunk, RetrievalLog
from .evaluation import metrics
from .retrieval import search
from .config import settings
from time import perf_counter

router=APIRouter(prefix='/api/evaluation',tags=['evaluation'])

class Case(BaseModel):
    id: str
    question: str = Field(min_length=1)
    reference_answer: str
    relevance: dict[str,int]
    type: str
    annotation_status: str = 'pending'

class Experiment(BaseModel):
    cases: list[Case] = Field(min_length=1,max_length=100)
    top_k: int = Field(default=5,ge=1,le=30)
    candidates: int = Field(default=20,ge=1,le=100)
    include_reranker: bool = False
    generate_answers: bool = False

@router.post('/run')
def run(experiment: Experiment):
    records=[]
    if experiment.generate_answers and not (settings.llm_api_key and settings.llm_model):
        raise HTTPException(503,'生成评估需要 LLM 配置')
    with DB() as db:
        for case in experiment.cases:
            if case.annotation_status != 'complete' or any(g<0 or g>3 for g in case.relevance.values()):
                raise HTTPException(422,'请完成人工标注；相关等级必须在 0 到 3 之间')
            existing=set(db.scalars(select(Chunk.id).where(Chunk.id.in_(case.relevance))))
            if existing != set(case.relevance): raise HTTPException(422,'标注引用了不存在的片段')
        variants=[('dense',False),('hybrid',False)]
        if experiment.include_reranker: variants.append(('hybrid',True))
        for case in experiment.cases:
            if experiment.generate_answers:
                from .generation import generate
                start=perf_counter()
                answer,_,_=generate(case.question,[],[],False)
                records.append({'case_id':case.id,'strategy':'baseline','answer':answer,
                                'reference_answer':case.reference_answer,'end_to_end_ms':(perf_counter()-start)*1000,
                                'accuracy':None,'accuracy_method':'pending human review'})
            for strategy,rerank in variants:
                start=perf_counter()
                found=search(db,case.question,strategy,experiment.top_k,experiment.candidates,rerank)
                record={'case_id':case.id,'question_type':case.type,'strategy':strategy,'rerank':rerank,
                        'metrics':metrics([r['id'] for r in found['results']],case.relevance,experiment.top_k),**found}
                if experiment.generate_answers:
                    answer,citations,_=generate(case.question,[],found['results'])
                    record.update(answer=answer,citations=citations,reference_answer=case.reference_answer,
                                  accuracy=None,accuracy_method='pending human review',end_to_end_ms=(perf_counter()-start)*1000)
                records.append(record)
        result={'scope':'retrieval_and_generation' if experiment.generate_answers else 'retrieval_only',
                'llm_model':settings.llm_model,'temperature':0,'embedding_model':settings.embedding_model,'reranker_model':settings.reranker_model,
                'parameters':experiment.model_dump(),'records':records,'accuracy':None,
                'limitations':'本次仅评估检索，未评估答案准确性；无相关证据样本不计算 Recall 和 nDCG。'}
        log=RetrievalLog(payload={'kind':'experiment','result':result});db.add(log);db.commit()
        return {'id':log.id,**result}

@router.get('/{experiment_id}')
def export(experiment_id:str):
    with DB() as db:
        log=db.get(RetrievalLog,experiment_id)
        if not log or log.payload.get('kind')!='experiment': raise HTTPException(404)
        return log.payload['result']
