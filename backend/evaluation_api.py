"""Explicit human annotations and reproducible retrieval experiments."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from .database import DB, Chunk, RetrievalLog
from .evaluation import metrics
from .retrieval import search
from .config import settings
from time import perf_counter
from .evaluation_summary import summarize
import hashlib,json

router=APIRouter(prefix='/api/evaluation',tags=['evaluation'])

class Case(BaseModel):
    id: str
    question: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1)
    relevance: dict[str,int]
    type: str
    annotation_status: str = 'pending'
    annotation_method: str = 'unspecified'

class Experiment(BaseModel):
    cases: list[Case] = Field(min_length=1,max_length=100)
    top_k: int = Field(default=5,ge=1,le=30)
    candidates: int = Field(default=20,ge=1,le=100)
    include_reranker: bool = False
    generate_answers: bool = False

@router.post('/run')
def run(experiment: Experiment):
    records=[]
    if len({case.id for case in experiment.cases})!=len(experiment.cases):
        raise HTTPException(422,'测试集问题 ID 不能重复')
    if experiment.candidates<experiment.top_k: raise HTTPException(422,'候选数不能小于 Top K')
    if experiment.generate_answers and not (settings.llm_api_key and settings.llm_model):
        raise HTTPException(503,'生成评估需要 LLM 配置')
    with DB() as db:
        for case in experiment.cases:
            if case.annotation_status != 'complete' or any(g<0 or g>3 for g in case.relevance.values()):
                raise HTTPException(422,'请完成人工标注；相关等级必须在 0 到 3 之间')
            if case.type!='out_of_scope' and not any(grade>0 for grade in case.relevance.values()):
                raise HTTPException(422,'库内问题至少需要一个相关片段标注')
            existing=set(db.scalars(select(Chunk.id).where(Chunk.id.in_(case.relevance))))
            if existing != set(case.relevance): raise HTTPException(422,'标注引用了不存在的片段')
        variants=[('dense',False),('hybrid',False)]
        if experiment.include_reranker: variants.append(('hybrid',True))
        for case in experiment.cases:
            if experiment.generate_answers:
                from .generation import generate,generation_info
                start=perf_counter()
                answer,_,_=generate(case.question,[],[],False)
                records.append({'case_id':case.id,'strategy':'baseline','answer':answer,
                                'generation':generation_info.get(),
                                'reference_answer':case.reference_answer,'end_to_end_ms':(perf_counter()-start)*1000,
                                'accuracy':None,'accuracy_method':'pending human review'})
            for strategy,rerank in variants:
                start=perf_counter()
                found=search(db,case.question,strategy,experiment.top_k,experiment.candidates,rerank)
                record={'case_id':case.id,'question_type':case.type,'strategy':strategy,'rerank':rerank,
                        'metrics':metrics([r['id'] for r in found['results']],case.relevance,experiment.top_k),**found}
                if experiment.generate_answers:
                    answer,citations,_=generate(case.question,[],found['results'])
                    record.update(answer=answer,citations=citations,reference_answer=case.reference_answer,generation=generation_info.get(),
                                  accuracy=None,accuracy_method='pending human review',end_to_end_ms=(perf_counter()-start)*1000)
                records.append(record)
        result={'scope':'retrieval_and_generation' if experiment.generate_answers else 'retrieval_only',
                'llm_model':settings.llm_model,'temperature':0,'max_tokens':settings.llm_max_tokens,'reasoning_effort':settings.llm_reasoning_effort,'embedding_model':settings.embedding_model,'reranker_model':settings.reranker_model,
                'parameters':experiment.model_dump(),'records':records,'accuracy':None,
                'code_version':settings.default_code_version,
                'dataset_hash':hashlib.sha256(json.dumps([c.model_dump() for c in experiment.cases],sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
                'summary':summarize(records),
                'limitations':'答案准确性须独立人工核验。无相关证据样本不计算 Recall 和 nDCG。延迟包含按需模型加载，正式实验应先预热并重复测量。'}
        log=RetrievalLog(payload={'kind':'experiment','result':result});db.add(log);db.commit()
        return {'id':log.id,**result}

@router.get('/{experiment_id}')
def export(experiment_id:str):
    with DB() as db:
        log=db.get(RetrievalLog,experiment_id)
        if not log or log.payload.get('kind')!='experiment': raise HTTPException(404)
        return log.payload['result']

class Review(BaseModel):
    record_index: int = Field(ge=0)
    score: float = Field(ge=0,le=1)
    reviewer: str = Field(min_length=1,max_length=100)
    notes: str = Field(min_length=1,max_length=4000)

@router.post('/{experiment_id}/reviews')
def review(experiment_id:str,annotation:Review):
    with DB() as db:
        log=db.scalar(select(RetrievalLog).where(RetrievalLog.id==experiment_id).with_for_update())
        if not log or log.payload.get('kind')!='experiment': raise HTTPException(404)
        payload=json.loads(json.dumps(log.payload)); result=payload['result']
        if annotation.record_index>=len(result['records']): raise HTTPException(422,'记录索引超出范围')
        record=result['records'][annotation.record_index]
        if 'answer' not in record: raise HTTPException(422,'仅可评分已生成的回答')
        record['human_review']=annotation.model_dump(exclude={'record_index'})
        record['accuracy']=annotation.score;record['accuracy_method']='human review'
        result['summary']=summarize(result['records'])
        log.payload=payload;db.commit()
        return result
