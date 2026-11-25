"""Shared helpers for the RAG notebooks.

Notebook 01 builds everything in here step by step; Notebooks 02-11 import it
so each notebook can focus on one concept.
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CHROMA_DIR = ROOT / ".chroma"
COLLECTION = "tac_corpus"

load_dotenv(ROOT / ".env")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


# ── models ──────────────────────────────────────────────────────────────────
def get_chat_model(**kwargs):
    from langchain.chat_models import init_chat_model
    return init_chat_model(MODEL, model_provider="openai", **kwargs)


def get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=EMBED_MODEL)


# ── loading (see Notebook 01) ───────────────────────────────────────────────
def ensure_corpus():
    if not (DATA_DIR / "manifest.json").exists():
        raise FileNotFoundError("Corpus not found. From the project root run:  uv run python scripts/generate_corpus.py")


def family(version: str) -> str:
    return ".".join(version.split(".")[:2])


def parse_front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        k, v = line.split(":", 1)
        v = v.strip()
        meta[k.strip()] = json.loads(v) if v.startswith('"') else v
    return meta, text[m.end():]


def load_markdown_dir(subdir: str) -> list[Document]:
    docs = []
    for path in sorted((DATA_DIR / subdir).glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        docs.append(Document(page_content=body.strip(), metadata={**meta, "source": f"{subdir}/{path.name}"}))
    return docs


def load_tickets() -> list[Document]:
    tickets = json.loads((DATA_DIR / "tickets" / "resolved_tickets.json").read_text(encoding="utf-8"))
    return [Document(
        page_content=f"{t['subject']}\n{t['description']}\nResolution: {t['resolution']}",
        metadata={"doc_id": t["ticket_id"], "doc_type": "ticket", "product": t["product"], "version": t["version"],
                  "version_family": family(t["version"]), "kb_refs": ",".join(t["kb_refs"]), "error_code": t["error_code"] or "none",
                  "source": "tickets/resolved_tickets.json"},
    ) for t in tickets]


def load_guides() -> list[Document]:
    from langchain_community.document_loaders import PyPDFLoader
    product_by_code = {"AR": "Aurora AR-900", "NF": "Nimbus NF-300", "OW": "Orion OW-20", "AT": "Atlas SD-WAN", "HX": "Helix HX-5000"}
    docs = []
    for path in sorted((DATA_DIR / "guides").glob("*.pdf")):
        for page in PyPDFLoader(str(path)).load():
            page.metadata = {"doc_id": path.stem, "doc_type": "guide", "product": product_by_code[path.stem.split("-")[1]],
                             "version_family": "all", "page": page.metadata.get("page", 0) + 1, "source": f"guides/{path.name}"}
            docs.append(page)
    return docs


def load_all_documents() -> list[Document]:
    ensure_corpus()
    return load_markdown_dir("kb") + load_markdown_dir("release_notes") + load_tickets() + load_guides()


def split_documents(docs, chunk_size: int = 800, chunk_overlap: int = 100) -> list[Document]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = f"{c.metadata['doc_id']}#{i}"
    return chunks


def load_chunks() -> list[Document]:
    return split_documents(load_all_documents())


# ── vector store (see Notebook 01) ──────────────────────────────────────────
def get_vectorstore(rebuild: bool = False):
    """Open the persisted Chroma collection built in Notebook 01 (builds it if missing)."""
    from langchain_chroma import Chroma
    vs = Chroma(collection_name=COLLECTION, embedding_function=get_embeddings(), persist_directory=str(CHROMA_DIR))
    if rebuild:
        vs.delete_collection()
        vs = Chroma(collection_name=COLLECTION, embedding_function=get_embeddings(), persist_directory=str(CHROMA_DIR))
    if rebuild or vs._collection.count() == 0:
        chunks = load_chunks()
        vs.add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])
    return vs


# ── formatting & evaluation helpers ─────────────────────────────────────────
def format_docs(docs) -> str:
    return "\n\n".join(f"[{d.metadata['doc_id']}] {d.page_content}" for d in docs)


def doc_ids(docs) -> list[str]:
    return list(dict.fromkeys(d.metadata["doc_id"] for d in docs))


def golden_set() -> list[dict]:
    ensure_corpus()
    return json.loads((DATA_DIR / "eval" / "golden_set.json").read_text(encoding="utf-8"))


def show(docs, expected=None, width: int = 90):
    """Print retrieved documents; mark expected ones with ✅."""
    for i, d in enumerate(docs, 1):
        mark = ("✅ " if d.metadata["doc_id"] in expected else "   ") if expected is not None else ""
        snippet = " ".join(d.page_content.split())[:width]
        print(f"{mark}{i}. [{d.metadata['doc_id']:<12}] {d.metadata['doc_type']:<12} {snippet}")


def hit(ids, expected) -> bool:
    return any(i in expected for i in ids)


def reciprocal_rank(ids, expected) -> float:
    return next((1 / r for r, i in enumerate(ids, 1) if i in expected), 0.0)


def chroma_filter(product: str | None = None, version: str | None = None, doc_type: str | None = None) -> dict | None:
    """Build a Chroma metadata filter. A version matches its family or 'all'."""
    conds = []
    if product:
        conds.append({"product": product})
    if version:
        conds.append({"version_family": {"$in": [family(version), "all"]}})
    if doc_type:
        conds.append({"doc_type": doc_type})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


# ── keyword (BM25) tokenization — see Notebook 05 ───────────────────────────
STOPWORDS = set("""a an and are as at be but by can do does for from has have how i if in is it its mean of on or our
should so that the their them there this to was we what when where which why will with you your about after any""".split())


def bm25_tokenize(text: str) -> list[str]:
    """Lower-case, keep codes like %ike-3-rekey_collision intact, strip trailing dots, drop stopwords."""
    toks = (t.rstrip(".") for t in re.findall(r"[%\w][\w\-\.%]*", text.lower()))
    return [t for t in toks if t and t not in STOPWORDS]
