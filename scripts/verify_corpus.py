"""Check that the generated corpus is complete and internally consistent.

    uv run python scripts/verify_corpus.py            # checks ./data
    uv run python scripts/verify_corpus.py --out DIR

Exit code 0 = all checks passed, 1 = at least one failure.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = {"kb": 30, "release_notes": 16, "tickets": 148, "guides": 5, "golden_questions": 40}


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return {k.strip(): json.loads(v) if v.strip().startswith('"') else v.strip()
            for k, v in (line.split(":", 1) for line in m.group(1).splitlines())} if m else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data"))
    data = Path(ap.parse_args().out)
    failures, checks = [], 0

    def check(ok: bool, msg: str):
        nonlocal checks
        checks += 1
        print(("  ✅ " if ok else "  ❌ ") + msg)
        if not ok:
            failures.append(msg)

    if not data.exists():
        sys.exit(f"No corpus at {data}. Run: uv run python scripts/generate_corpus.py")

    kb = {front_matter(p).get("doc_id"): front_matter(p) for p in sorted((data / "kb").glob("*.md"))}
    rn = {front_matter(p).get("doc_id"): front_matter(p) for p in sorted((data / "release_notes").glob("*.md"))}
    tickets = json.loads((data / "tickets" / "resolved_tickets.json").read_text(encoding="utf-8"))
    guides = {p.stem: p for p in sorted((data / "guides").glob("*.pdf"))}
    golden = json.loads((data / "eval" / "golden_set.json").read_text(encoding="utf-8"))
    all_ids = set(kb) | set(rn) | set(guides) | {t["ticket_id"] for t in tickets}

    print("Counts")
    for name, n in [("kb", len(kb)), ("release_notes", len(rn)), ("tickets", len(tickets)), ("guides", len(guides)), ("golden_questions", len(golden))]:
        check(n == EXPECTED[name], f"{name}: {n} (expected {EXPECTED[name]})")

    print("Metadata")
    check(all(m.get("doc_id") and m.get("product") and m.get("version_family") for m in kb.values()), "every KB article has doc_id, product, version_family")
    check(all(m.get("version") for m in rn.values()), "every release note has a version")
    check(len({t["ticket_id"] for t in tickets}) == len(tickets), "ticket IDs are unique")

    print("Cross-references")
    bad_refs = [r for t in tickets for r in t["kb_refs"] if r not in kb]
    check(not bad_refs, f"all ticket kb_refs resolve ({len(bad_refs)} broken)")
    rn_text = " ".join((data / "release_notes" / f"{i}.md").read_text(encoding="utf-8") for i in rn)
    rn_kbs = set(re.findall(r"KB-\d{4}", rn_text))
    check(rn_kbs <= set(kb), f"all KB IDs mentioned in release notes exist ({len(rn_kbs - set(kb))} missing)")
    fixed_links = [(k, m["fixed_in"]) for k, m in kb.items() if m.get("fixed_in") not in ("n/a", None)]
    missing_rn = [k for k, v in fixed_links if not any(r.endswith(f"-{v}") and k in (data / "release_notes" / f"{r}.md").read_text(encoding="utf-8") for r in rn)]
    check(not missing_rn, f"every fixed KB is listed in its fix release notes ({missing_rn or 'ok'})")

    print("Golden set")
    bad_golden = [g["id"] for g in golden for d in g["expected_doc_ids"] if d not in all_ids]
    check(not bad_golden, f"every expected doc_id exists ({sorted(set(bad_golden)) or 'ok'})")
    check(all(g["expected_doc_ids"] for g in golden if g["type"] != "unanswerable"), "answerable questions have expected documents")
    check(all(not g["expected_doc_ids"] for g in golden if g["type"] == "unanswerable"), "unanswerable questions have none")
    for code in {"%SYS-4-CPU_HIGH", "%TRANSCEIVER-3-RX_POWER_LOW"}:
        check(sum(1 for m in kb.values() if m.get("error_code") == code) == 2, f"near-duplicate pair present for {code}")

    print("PDF guides")
    for gid, path in guides.items():
        reader = PdfReader(str(path))
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        check(len(reader.pages) >= 5 and gid in text, f"{gid}: {len(reader.pages)} pages, text extractable")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
