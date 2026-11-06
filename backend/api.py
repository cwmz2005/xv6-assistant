import time
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from .database import DB, Base, engine, Session, Message, Document, Chunk
from .retrieval import search
from .ingestion import ingest
from .config import settings
app=FastAPI(title="xv6 RAG")
class Query(BaseModel):
    query: str = Field(min_length=1,max_length=8000)
    strategy: str = Field(default="hybrid",pattern="^(dense|bm25|hybrid)$")
    top_k: int = Field(default=5,ge=1,le=30)
    candidates: int = Field(default=20,ge=1,le=100)
    rerank: bool = False
    rrf_k: int = Field(default=60,ge=1)
class Chat(Query):
    session_id: str
    rag: bool = True
class Import(BaseModel):
    root: str
    commit: str
@app.post("/api/import")
def import_data(q: Import):
    with DB() as db: return {"chunks":ingest(db,q.root,q.commit)}
@app.post("/api/search")
def retrieve(q:Query):
    with DB() as db: return search(db,**q.model_dump())
@app.get("/api/documents")
def documents():
    with DB() as db: return [{"id":d.id,"path":d.path,"commit":d.version,"hash":d.content_hash} for d in db.scalars(select(Document))]
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
    if not settings.llm_api_key or not settings.llm_model: raise HTTPException(503,"??? LLM_API_KEY ? LLM_MODEL")
    from langchain_openai import ChatOpenAI
    t=time.perf_counter()
    with DB() as db:
        session=db.get(Session,q.session_id)
        if not session: raise HTTPException(404,"?????")
        history=list(db.scalars(select(Message).where(Message.session_id==q.session_id).order_by(Message.sequence)))
        found=search(db,**q.model_dump(exclude={"session_id","rag"})) if q.rag else {"results":[]}
        evidence=found["results"]
        prompt="?? xv6 ??????????????????????????????????????????????? [????ID]??????ID???????????" if q.rag else "?? xv6 ????????????????????????????"
        msgs=[("system",prompt)]+[(m.role,m.content) for m in history[-12:]]+[("user",str({"question":q.query,"evidence":evidence}))]
        llm=ChatOpenAI(model=settings.llm_model,api_key=settings.llm_api_key,base_url=settings.llm_base_url or None,temperature=0)
        answer=str(llm.invoke(msgs).content)
        citations=[r for r in evidence if "["+r["id"]+"]" in answer]
        session.title=q.query[:80]
        db.add_all([Message(session_id=q.session_id,role="user",content=q.query,sequence=len(history)),Message(session_id=q.session_id,role="assistant",content=answer,citations=citations,sequence=len(history)+1)])
        db.commit(); return {"answer":answer,"citations":citations,"retrieval":found,"end_to_end_ms":(time.perf_counter()-t)*1000}
app.mount("/",StaticFiles(directory="frontend",html=True),name="frontend")
