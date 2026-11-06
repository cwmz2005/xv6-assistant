import time
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy import func
from .database import DB, Base, engine, Session, Message, Document, Chunk
from .retrieval import search
from .ingestion import ingest
from .config import settings
app=FastAPI(title="xv6 RAG")
from .evaluation_api import router as evaluation_router
app.include_router(evaluation_router)
class Query(BaseModel):
    query: str = Field(min_length=1,max_length=8000)
    strategy: str = Field(default="hybrid",pattern="^(dense|bm25|hybrid)$")
    top_k: int = Field(default=5,ge=1,le=30)
    candidates: int = Field(default=20,ge=1,le=100)
    rerank: bool = False
    rrf_k: int = Field(default=60,ge=1)
    version: str | None = None
class Chat(Query):
    session_id: str
    rag: bool = True
    tools: bool = False
class Import(BaseModel):
    root: str
    commit: str | None = None

@app.get('/api/versions')
def versions():
    with DB() as db:
        return list(db.scalars(select(Document.version).distinct().where(~Document.version.like('directory-%'))))
@app.post("/api/import")
def import_data(q: Import):
    with DB() as db: return {"chunks":ingest(db,q.root,q.commit)}
@app.post("/api/search")
def retrieve(q:Query):
    with DB() as db: return search(db,**q.model_dump())
@app.get("/api/documents")
def documents():
    with DB() as db:
        rows=db.execute(select(Document,func.count(Chunk.id)).outerjoin(Chunk,Chunk.document_id==Document.id).group_by(Document.id)).all()
        return [{"id":d.id,"path":d.path,"commit":d.version,"source":d.source,"hash":d.content_hash,"chunks":count,"is_system":d.is_system} for d,count in rows]

@app.delete('/api/documents/{document_id}')
def delete_document(document_id:str):
    with DB() as db:
        document=db.scalar(select(Document).where(Document.id==document_id).with_for_update())
        if not document: raise HTTPException(404,'文档不存在')
        if document.is_system: raise HTTPException(403,'系统文档受保护，不能删除')
        db.delete(document)
        db.commit()
        return {'deleted':document_id}

@app.get('/api/documents/{document_id}/chunks')
def document_chunks(document_id:str):
    with DB() as db:
        return [{'id':c.id,'text':c.text,'location':c.location} for c in db.scalars(select(Chunk).where(Chunk.document_id==document_id))]
@app.get("/api/sessions")
def sessions():
    with DB() as db: return [{"id":s.id,"title":s.title} for s in db.scalars(select(Session))]
@app.post("/api/sessions")
def create_session():
    with DB() as db:
        s=Session(); db.add(s); db.commit(); return {"id":s.id}
@app.get("/api/sessions/{sid}/messages")
def messages(sid:str):
    with DB() as db: return [{"role":m.role,"content":m.content,"citations":m.citations} for m in db.scalars(select(Message).where(Message.session_id==sid).order_by(Message.sequence))]
@app.delete("/api/sessions/{sid}")
def remove(sid:str):
    with DB() as db:
        s=db.get(Session,sid)
        if not s: raise HTTPException(404)
        db.delete(s); db.commit(); return {"deleted":sid}
@app.post("/api/chat")
def chat(q:Chat):
    if not settings.llm_api_key or not settings.llm_model: raise HTTPException(503,"请配置 LLM_API_KEY 和 LLM_MODEL")
    from langchain_openai import ChatOpenAI
    t=time.perf_counter()
    with DB() as db:
        session=db.get(Session,q.session_id)
        if not session: raise HTTPException(404,"会话不存在")
        history=list(db.scalars(select(Message).where(Message.session_id==q.session_id).order_by(Message.sequence)))
        found=search(db,**q.model_dump(exclude={"session_id","rag","tools"})) if q.rag else {"results":[]}
        evidence=found["results"]
        from .generation import generate
        answer,citations,tool_log=generate(q.query,history,evidence,q.rag,
            (lambda query: search(db,query,q.strategy,q.top_k,q.candidates,q.rerank,q.rrf_k,q.version)) if q.tools and q.rag else None)
        session.title=q.query[:80]
        db.add_all([Message(session_id=q.session_id,role="user",content=q.query,sequence=len(history)),Message(session_id=q.session_id,role="assistant",content=answer,citations=citations,sequence=len(history)+1)])
        db.commit(); return {"answer":answer,"citations":citations,"retrieval":found,"tool_calls":tool_log,"end_to_end_ms":(time.perf_counter()-t)*1000}
@app.post('/api/chat/stream')
def stream_chat(q: Chat):
    import json
    import queue
    import threading
    from fastapi.responses import StreamingResponse
    from .generation import token_sink
    events=queue.Queue()
    def worker():
        context=token_sink.set(lambda token: events.put(('token',{'text':token})))
        try:
            events.put(('done',chat(q)))
        except Exception as exc:
            events.put(('error',{'message':str(exc)}))
        finally:
            token_sink.reset(context)
    threading.Thread(target=worker,daemon=True).start()
    def stream():
        while True:
            try: kind,payload=events.get(timeout=15)
            except queue.Empty:
                yield ': keepalive\n\n'
                continue
            yield f'event: {kind}\ndata: {json.dumps(payload,ensure_ascii=False)}\n\n'
            if kind in {'done','error'}: break
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

from pathlib import Path
frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
