import hashlib
import subprocess
from functools import lru_cache
from pathlib import Path

from sqlalchemy import delete, select

from ..core.config import settings
from ..core.database import Chunk, Document
from .chunking import split


@lru_cache(maxsize=1)
def embedder():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def git(repo, *args):
    return subprocess.check_output(
        [
            "git",
            "-c",
            f"safe.directory={Path(repo).resolve().as_posix()}",
            "-C",
            repo,
            *args,
        ]
    )


def ingest(db, root, commit=None, progress=None):
    repo = str(Path(root).resolve())
    project_root = Path(__file__).resolve().parents[1]
    is_system = Path(repo) in {
        (project_root / "data").resolve(),
        (project_root / "data/labs").resolve(),
        (project_root / "data/xv6-labs-2022-impl").resolve(),
    }
    if commit:
        version = git(repo, "rev-parse", commit + "^{commit}").decode().strip()
        paths = git(repo, "ls-tree", "-r", "--name-only", version).decode().splitlines()

        def entries():
            for path in paths:
                if Path(path).suffix.lower() not in {".md", ".txt", ".c", ".h", ".s"}:
                    continue
                content = git(repo, "show", f"{version}:{path}").decode(
                    "utf-8", errors="replace"
                )
                yield path, content, hashlib.sha256(content.encode()).hexdigest()
    else:
        if (Path(repo) / ".git").exists():
            raise ValueError("Git repositories require an explicit audited commit")
        from .sources import directory_files

        version = "directory-v1"

        def entries():
            return directory_files(repo)

    count = 0
    for processed, (path, content, digest) in enumerate(entries(), 1):
        if progress:
            progress(
                {"processed": processed - 1, "current_path": path, "chunks": count}
            )
        if (
            not commit
            and Path(repo) == (project_root / "data").resolve()
            and not path.endswith(".pdf")
        ):
            continue
        doc = db.scalar(
            select(Document).where(
                Document.source == repo,
                Document.version == version,
                Document.path == path,
            )
        )
        profile = (
            f"pdf-v2:{settings.embedding_model}"
            if path.endswith(".pdf")
            else ("html-v2" if path.endswith(".html") else "legacy")
        )
        if doc and doc.content_hash == digest and doc.index_profile == profile:
            continue
        if not doc:
            doc = Document(
                source=repo,
                version=version,
                path=path,
                content_hash=digest,
                is_system=is_system,
            )
            db.add(doc)
            db.flush()
        else:
            db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
            doc.content_hash = digest
        doc.index_profile = profile
        if path.endswith(".pdf"):
            from .pdf_source import pdf_chunks

            pieces = list(pdf_chunks(Path(repo) / path))
        else:
            pieces = list(split(content, path))
        texts = [p[0] for p in pieces]
        cached = {}
        if texts and not path.endswith(".pdf"):
            for chunk in db.scalars(select(Chunk).where(Chunk.text.in_(texts))):
                cached[chunk.text] = chunk.embedding
        missing = list(dict.fromkeys(body for body in texts if body not in cached))
        if missing:
            cached.update(
                zip(
                    missing,
                    embedder().embed_documents(
                        ["passage: " + body for body in missing]
                    ),
                )
            )
        vectors = [cached[body] for body in texts]
        for (body, loc), vec in zip(pieces, vectors):
            cid = hashlib.sha256(
                f"{repo}:{version}:{path}:{loc}:{body}".encode()
            ).hexdigest()
            db.add(
                Chunk(
                    id=cid,
                    document_id=doc.id,
                    text=body,
                    embedding=vec,
                    location={
                        **loc,
                        "path": path,
                        "commit": version,
                        "source": repo,
                        "line_basis": loc.get(
                            "line_basis",
                            "extracted_text" if path.endswith(".html") else "original",
                        ),
                    },
                )
            )
            count += 1
    db.commit()
    return count
