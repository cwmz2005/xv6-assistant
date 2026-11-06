import hashlib, re, subprocess
from pathlib import Path
from sqlalchemy import select, delete
from .database import Document, Chunk
from functools import lru_cache
from .config import settings
@lru_cache(maxsize=1)
def embedder():
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=settings.embedding_model, model_kwargs={"device":"cpu"}, encode_kwargs={"normalize_embeddings":True})
from .chunking import split
def git(repo, *args):
    return subprocess.check_output(["git","-c",f"safe.directory={Path(repo).resolve().as_posix()}","-C",repo,*args])
def ingest(db, root, commit):
    repo = str(Path(root).resolve())
    if not commit: raise ValueError("必须指定已核验的原始 Git 提交")
    version = git(repo,"rev-parse",commit+"^{commit}").decode().strip()
    paths = git(repo,"ls-tree","-r","--name-only",version).decode().splitlines()
    count=0
    for path in paths:
        if Path(path).suffix.lower() not in {".md",".txt",".c",".h",".s",".html"}: continue
        content=git(repo,"show",f"{version}:{path}").decode("utf-8",errors="replace")
        digest=hashlib.sha256(content.encode()).hexdigest()
        doc=db.scalar(select(Document).where(Document.source==repo,Document.version==version,Document.path==path))
        if doc and doc.content_hash==digest: continue
        if not doc:
            doc=Document(source=repo,version=version,path=path,content_hash=digest); db.add(doc); db.flush()
        else:
            db.execute(delete(Chunk).where(Chunk.document_id==doc.id)); doc.content_hash=digest
        pieces=list(split(content,path))
        vectors=embedder().embed_documents(["passage: "+p[0] for p in pieces]) if pieces else []
        for (body,loc),vec in zip(pieces,vectors):
            cid=hashlib.sha256(f"{repo}:{version}:{path}:{loc['start_line']}:{body}".encode()).hexdigest()
            db.add(Chunk(id=cid,document_id=doc.id,text=body,embedding=vec,location={**loc,"commit":version})); count+=1
    db.commit(); return count
