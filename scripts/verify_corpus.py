"""Check that the generated corpus is complete, internally consistent and faithful to its facts.

    uv run python scripts/verify_corpus.py            # checks ./data
    uv run python scripts/verify_corpus.py --out DIR

Expected counts come from data/manifest.json and ground truth from data/facts.json,
so the checks follow whatever corpus_brief.toml asked for.
Exit code 0 = all checks passed, 1 = at least one failure.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
DOC_ID_RE = re.compile(r"\b(?:KB-\d{4}|TKT-\d{5}|RN-[A-Z]{2}-[\d.]*\d|GUIDE-[A-Z]{2})\b")
ARTIFACT_RE = re.compile(r"\{[a-z_]+[\[\}]|\bas an ai\b|lorem ipsum|\bTODO\b|\[insert|<placeholder>", re.I)


def split_front_matter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    meta = {k.strip(): json.loads(v) if v.strip().startswith('"') else v.strip()
            for k, v in (line.split(":", 1) for line in m.group(1).splitlines())}
    return meta, text[m.end():]


def section(body: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    return m.group(1) if m else ""


def norm(s: str) -> str:
    return " ".join(s.split())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")             # ✅/❌ on Windows consoles and pipes
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

    if not (data / "manifest.json").exists():
        sys.exit(f"No corpus at {data}. Run: uv run python scripts/generate_corpus.py")

    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    facts = json.loads((data / "facts.json").read_text(encoding="utf-8"))
    issues, prods = facts["issues"], facts["products"]
    by_kb = {i["kb"]: i for i in issues}
    kb = {m["doc_id"]: (m, b) for m, b in (split_front_matter(p) for p in sorted((data / "kb").glob("*.md")))}
    rn = {m["doc_id"]: (m, b) for m, b in (split_front_matter(p) for p in sorted((data / "release_notes").glob("*.md")))}
    tickets = json.loads((data / "tickets" / "resolved_tickets.json").read_text(encoding="utf-8"))
    guides = {p.stem: PdfReader(str(p)) for p in sorted((data / "guides").glob("*.pdf"))}
    guide_text = {g: norm(" ".join(pg.extract_text() or "" for pg in r.pages)) for g, r in guides.items()}
    golden = json.loads((data / "eval" / "golden_set.json").read_text(encoding="utf-8"))
    all_ids = set(kb) | set(rn) | set(guides) | {t["ticket_id"] for t in tickets}
    doc_text = {**{k: b for k, (_, b) in kb.items()}, **{k: b for k, (_, b) in rn.items()}, **guide_text,
                **{t["ticket_id"]: f"{t['subject']} {t['description']} {t['resolution']}" for t in tickets}}

    print("Counts (from manifest.json and facts.json)")
    actual = {"kb": len(kb), "release_notes": len(rn), "tickets": len(tickets), "guides": len(guides), "golden_questions": len(golden)}
    for name, n in actual.items():
        check(n == manifest["counts"][name], f"{name}: {n} (manifest {manifest['counts'][name]})")
    check(set(kb) == set(by_kb), f"one KB article per fact issue ({len(by_kb)})")
    check(set(rn) == {f"RN-{c}-{v}" for c, p in prods.items() for v in p["versions"]}, "one release note per product release")
    check(set(guides) == {p["guide"]["id"] for p in prods.values()}, "one guide per product")

    print("Metadata")
    check(all(m.get("doc_id") and m.get("product") and m.get("version_family") for m, _ in kb.values()), "every KB article has doc_id, product, version_family")
    mism = [k for k, (m, _) in kb.items() if m["error_code"] != (by_kb[k]["code"] or "none") or m["fixed_in"] != (by_kb[k]["fixed_in"] or "n/a")
            or m["product"] != prods[by_kb[k]["p"]]["name"]]
    check(not mism, f"KB front matter matches facts ({mism or 'ok'})")
    fam_bad = [k for k, i in by_kb.items() if i["affected"] != "all" and len({".".join(v.split(".")[:2]) for v in i["affected"]}) != 1]
    check(not fam_bad, f"each KB's affected versions share one version family ({fam_bad or 'ok'})")
    check(all(m.get("version") for m, _ in rn.values()), "every release note has a version")
    check(len({t["ticket_id"] for t in tickets}) == len(tickets), "ticket IDs are unique")

    print("Cross-references")
    bad_refs = [r for t in tickets for r in t["kb_refs"] if r not in kb]
    check(not bad_refs, f"all ticket kb_refs resolve ({len(bad_refs)} broken)")
    mentioned = {i for txt in doc_text.values() for i in DOC_ID_RE.findall(txt)}
    check(mentioned <= all_ids, f"every document ID mentioned in any document exists ({sorted(mentioned - all_ids) or 'ok'})")
    missing_rn = [k for k, i in by_kb.items() if i["fixed_in"] and k not in section(rn[f"RN-{i['p']}-{i['fixed_in']}"][1], "Resolved issues")]
    check(not missing_rn, f"every fixed KB is listed under Resolved issues in its fix release notes ({missing_rn or 'ok'})")

    print("Retrieval traps (from facts.json)")
    for code, p in prods.items():
        twins = [i for i in issues if i["p"] == code and "version_twin" in i["traps"]]
        fams = {".".join(i["affected"][0].split(".")[:2]) for i in twins if i["affected"] != "all"}
        check(len(twins) >= 2 and len(fams) >= 2, f"{p['name']}: version-twin pair in different version families ({[i['kb'] for i in twins]})")
        dups = [i for i in issues if i["p"] == code and i["duplicate_of"]]
        ok = bool(dups) and all(by_kb[d["duplicate_of"]]["code"] == d["code"] and d["code"] for d in dups)
        check(ok, f"{p['name']}: near-duplicate pair shares an error code ({[(d['kb'], d['duplicate_of'], d['code']) for d in dups]})")

    print("Faithfulness to facts")
    bad = [k for k, (_, b) in kb.items() if by_kb[k]["code"] and by_kb[k]["code"] not in section(b, "Diagnosis")]
    check(not bad, f"each KB shows its log message in the diagnosis output ({bad or 'ok'})")
    bad = [k for k, (_, b) in kb.items() if by_kb[k]["fixed_in"] and by_kb[k]["fixed_in"] not in section(b, "Resolution")]
    check(not bad, f"each KB resolution names its fix release ({bad or 'ok'})")
    bad = [k for k, (_, b) in kb.items() if any(c not in b for c in by_kb[k]["workaround_commands"])]
    check(not bad, f"each KB contains its workaround commands ({bad or 'ok'})")
    bad = [t["ticket_id"] for t in tickets if t["error_code"] and t["error_code"] not in t["description"]]
    check(not bad, f"tickets with an error_code quote it in the description ({len(bad)} bad)")
    bad = [t["ticket_id"] for t in tickets for r in t["kb_refs"] if by_kb[r]["code"] and not t["error_code"] and by_kb[r]["code"] in doc_text[t["ticket_id"]]]
    check(not bad, f"tickets without an error_code do not contain one ({len(bad)} bad)")
    bad = [t["ticket_id"] for t in tickets if t["kb_refs"] and not all(r in t["resolution"] for r in t["kb_refs"])]
    check(not bad, f"issue tickets cite their KB in the resolution ({len(bad)} bad)")
    for gid, txt in guide_text.items():
        g = next(p["guide"] for p in prods.values() if p["guide"]["id"] == gid)
        missing = [c for s in g["sections"] for c in s["commands"] if norm(c) not in txt]
        check(not missing, f"{gid}: all section commands present ({missing[:3] or 'ok'})")

    print("Writing quality")
    kb_words = {k: len(b.split()) for k, (_, b) in kb.items()}
    check(all(350 <= n <= 1300 for n in kb_words.values()), f"KB length {min(kb_words.values())}-{max(kb_words.values())} words (350-1300)")
    rn_words = {k: len(b.split()) for k, (_, b) in rn.items()}
    check(all(150 <= n <= 1200 for n in rn_words.values()), f"release-note length {min(rn_words.values())}-{max(rn_words.values())} words (150-1200)")
    check(all(len(t["description"].split()) >= 25 for t in tickets), "every ticket description has at least 25 words")
    arts = [i for i, txt in doc_text.items() if ARTIFACT_RE.search(txt)]
    check(not arts, f"no template or LLM artifacts ({arts[:5] or 'ok'})")

    print("Golden set")
    bad_golden = [g["id"] for g in golden for d in g["expected_doc_ids"] if d not in all_ids]
    check(not bad_golden, f"every expected doc_id exists ({sorted(set(bad_golden)) or 'ok'})")
    check(all(g["expected_doc_ids"] for g in golden if g["type"] != "unanswerable"), "answerable questions have expected documents")
    check(all(not g["expected_doc_ids"] for g in golden if g["type"] == "unanswerable"), "unanswerable questions have none")
    check(len({g["question"] for g in golden}) == len(golden), "questions are unique")
    for g in [g for g in golden if g["type"] == "error_code"]:
        code = next((c for c in {i["code"] for i in issues if i["code"]} if c in g["question"]), None)
        check(code is not None and all(code in doc_text[d] for d in g["expected_doc_ids"]),
              f"{g['id']} error_code: every expected document contains {code}")
    for g in [g for g in golden if g["type"] in ("version_specific", "multi_hop")]:
        check(g["filters"].get("version", "") in g["question"], f"{g['id']} {g['type']}: question names its version {g['filters'].get('version')}")
    check(set(manifest["golden_types"]) == {g["type"] for g in golden}, f"golden types {manifest['golden_types']}")

    print("PDF guides")
    for gid, reader in guides.items():
        check(len(reader.pages) >= 8 and gid in guide_text[gid], f"{gid}: {len(reader.pages)} pages, text extractable")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
