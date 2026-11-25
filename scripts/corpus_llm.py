"""Cached, validated structured-output LLM calls for the corpus generator.

Every call is keyed by a hash of (stage, output schema, system prompt, user prompt).
A validated result is saved to scripts/llm_cache/<stage>/<key>.json, so re-running
the generator replays the cache and reproduces the corpus byte-for-byte without
an API key. The model name is recorded in each cache file but is deliberately not
part of the key: a different OPENAI_MODEL in .env still reuses the shared cache.

Modes:
    default  use the cache, call the LLM on a miss
    refresh  ignore the cache and regenerate (overwrites cache files)
    offline  never call the LLM; a cache miss is an error
"""

import hashlib
import json
import os
import sys
import threading
from collections import Counter
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(__file__).resolve().parent / "llm_cache"
T = TypeVar("T", bound=BaseModel)
Check = Callable[[BaseModel], list[str]]


class CacheMiss(RuntimeError):
    pass


class LLM:
    def __init__(self, mode: str = "default", workers: int = 8, attempts: int = 4):
        assert mode in ("default", "refresh", "offline"), mode
        load_dotenv(ROOT / ".env")
        self.model = os.getenv("CORPUS_MODEL") or os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        self.mode, self.workers, self.attempts = mode, workers, attempts
        self.stats: Counter = Counter()
        self.used: set[Path] = set()                 # cache files read or written by this run
        self._chat = None
        self._lock = threading.Lock()

    # ── public API ──────────────────────────────────────────────────────────
    def generate(self, stage: str, label: str, schema: type[T], system: str, user: str,
                 check: Check | None = None, attempts: int | None = None) -> T:
        key = hashlib.sha256(json.dumps([stage, schema.__name__, sorted(schema.model_fields), system, user]).encode()).hexdigest()[:24]
        path = CACHE_DIR / stage / f"{key}.json"
        if self.mode != "refresh" and path.exists():
            out = schema.model_validate(json.loads(path.read_text(encoding="utf-8"))["output"])
            if not (check(out) if check else []):
                self.used.add(path)
                self._count("cached")
                return out
            if self.mode == "offline":
                raise CacheMiss(f"{stage}/{label}: cached output no longer passes validation; re-run without --offline.")
        if self.mode == "offline":
            raise CacheMiss(f"{stage}/{label}: not in scripts/llm_cache; re-run without --offline (needs OPENAI_API_KEY).")

        messages = [("system", system), ("human", user)]
        errs: list[str] = []
        attempts = attempts or self.attempts
        for attempt in range(1, attempts + 1):
            out = None
            try:
                out = self._structured(schema).invoke(messages)
                errs = ["Empty response."] if out is None else (check(out) if check else [])
            except CacheMiss:
                raise
            except Exception as e:                      # schema/parse errors, refusals, transient API errors
                errs = [f"{type(e).__name__}: {str(e)[:600]}"]
            if not errs:
                path.parent.mkdir(parents=True, exist_ok=True)
                record = {"stage": stage, "label": label, "model": self.model, "output": out.model_dump(mode="json")}
                path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
                self.used.add(path)
                self._count("generated")
                self._log(f"  · {stage:<16} {label:<22} generated" + (f" (attempt {attempt})" if attempt > 1 else ""))
                return out
            self._count("retries")
            self._log(f"  ! {stage:<16} {label:<22} attempt {attempt} rejected: {errs[0][:160]}")
            if out is not None:
                messages = messages + [("ai", out.model_dump_json()),
                                       ("human", "Your answer has these problems. Return a corrected, complete answer:\n- " + "\n- ".join(errs))]
        raise RuntimeError(f"{stage}/{label}: no valid output after {attempts} attempts: {errs}")

    def map(self, fn: Callable, items: Iterable) -> list:
        """Run fn over items concurrently; results keep the input order."""
        items = list(items)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(fn, items))

    def prune(self) -> int:
        """Delete cache files this run did not use (e.g. outputs for prompts that have since changed)."""
        stale = [p for p in CACHE_DIR.rglob("*.json") if p not in self.used]
        for p in stale:
            p.unlink()
        return len(stale)

    # ── internals ───────────────────────────────────────────────────────────
    def _structured(self, schema):
        with self._lock:
            if self._chat is None:
                if not os.getenv("OPENAI_API_KEY"):
                    raise CacheMiss("OPENAI_API_KEY is not set (see .env.example).")
                from langchain.chat_models import init_chat_model
                self._chat = init_chat_model(self.model, model_provider="openai", timeout=300, max_retries=3)
        return self._chat.with_structured_output(schema, method="json_schema", strict=True)

    def _count(self, k: str):
        with self._lock:
            self.stats[k] += 1

    def _log(self, msg: str):
        with self._lock:
            print(msg, file=sys.stderr, flush=True)
