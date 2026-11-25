"""Generate the synthetic TAC knowledge corpus used by the RAG notebooks, with an LLM.

    uv run python scripts/generate_corpus.py             # writes ./data (replays scripts/llm_cache, calls the LLM on a miss)
    uv run python scripts/generate_corpus.py --offline   # rebuild from the cache only: no API key, no cost
    uv run python scripts/generate_corpus.py --refresh   # regenerate everything with the LLM
    uv run python scripts/generate_corpus.py --out DIR --issues-per-product 8 --tickets-per-issue 3

Pipeline (domain, products and quotas come from scripts/corpus_brief.toml):
  1. facts      the LLM invents issues, error codes, release features, guide topics, customers and
                unanswerable questions, validated against the brief          -> data/facts.json
  2. documents  the LLM writes KB articles, release notes, resolved tickets and PDF guides grounded on
                the facts; IDs, metadata and cross-references are always filled in by code
  3. golden     rules pick the evaluation targets and compute expected documents; the LLM only words
                the questions and reference answers                           -> data/eval/golden_set.json

Deterministic given the seed and the LLM cache: same inputs -> byte-identical output (PDFs included).
"""

import argparse
import json
import random
import re
import shutil
import sys
import tomllib
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

import corpus_prompts as P
from corpus_llm import LLM, CacheMiss
from corpus_schemas import (DuplicateDraft, GlobalFacts, GoldenPhrasing, GuideFront, GuidePlan, GuideSectionBody, KBBody, ProductIssues,
                            ReleaseNoteBody, TicketBatch, validate_global, validate_guide_plan, validate_product_issues, vkey)

SEED = 42
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
DOC_ID_RE = re.compile(r"\b(?:KB-\d{4}|TKT-\d{5}|RN-[A-Z]{2}-[\d.]*\d|GUIDE-[A-Z]{2})\b")
FIXED_IN_RE = re.compile(r"\b[Ff]ixed in (?:release |version |software )?(\d+\.\d+(?:\.\d+)?)")


# ── helpers ─────────────────────────────────────────────────────────────────
def affected_str(issue) -> str:
    return "All versions" if issue["affected"] == "all" else ", ".join(issue["affected"])


def version_family(issue) -> str:
    return "all" if issue["affected"] == "all" else ".".join(issue["affected"][0].split(".")[:2])


def rn_id(p: str, v: str) -> str:
    return f"RN-{p}-{v}"


def front_matter(meta: dict) -> str:
    lines = ["---"] + [f"{k}: {json.dumps(v) if isinstance(v, str) else v}" for k, v in meta.items()] + ["---", ""]
    return "\n".join(lines)


def numbered(steps: list[str]) -> str:
    return "\n".join(f"{i}. {s.strip()}" for i, s in enumerate(steps, 1))


def stray_ids(text: str, allowed=()) -> list[str]:
    return sorted(set(DOC_ID_RE.findall(text)) - set(allowed))


def nwords(*parts) -> int:
    return sum(len(str(p).split()) for p in parts)


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8", newline="\n")


# ── Stage 1: facts ──────────────────────────────────────────────────────────
def build_facts(llm: LLM, brief: dict) -> dict:
    print("Stage 1/3: facts")
    sysmsg, c, t = P.system(brief), brief["counts"], brief["traps"]
    prods = brief["products"]

    def gen_issues(p):
        return llm.generate("facts_issues", p["code"], ProductIssues, sysmsg, P.product_issues(brief, p),
                            check=lambda o: validate_product_issues(o, p["versions"], c, t), attempts=6)

    drafts = llm.map(gen_issues, prods)
    issues, features = [], {}
    for p, pi in zip(prods, drafts):
        ids = {d.ref: f"KB-{p['kb_prefix']}{n:02d}" for n, d in enumerate(pi.issues, 1)}
        twin: dict[str, str] = {}
        for d in pi.issues:
            if d.twin_of:
                twin[d.ref] = d.twin_of
                twin.setdefault(d.twin_of, d.ref)
        dup_targets = {d.duplicate_of for d in pi.issues if d.duplicate_of}
        for d in pi.issues:
            issues.append({
                "kb": ids[d.ref], "p": p["code"], "category": d.category, "code": d.error_code, "title": d.title,
                "symptoms": d.symptoms, "root_cause": d.root_cause, "workaround": d.workaround,
                "workaround_commands": d.workaround_commands, "fix": d.fix,
                "affected": "all" if d.affects_all_versions else sorted(d.affected_versions, key=vkey),
                "fixed_in": d.fixed_in, "q": None if d.duplicate_of else d.engineer_question,
                "traps": (["version_twin"] if d.ref in twin else []) + (["near_duplicate"] if d.duplicate_of or d.ref in dup_targets else []),
                "twin_of": ids.get(twin.get(d.ref, "")), "duplicate_of": ids.get(d.duplicate_of or ""),
            })
        features[p["code"]] = {v: next(r.features for r in pi.releases if r.version == v) for v in p["versions"]}

    # Near-duplicates: the LLM only chooses which issue gets a second article. That article is rewritten from
    # the original here, and code copies the original's versions, fix, log message and commands, so the pair is
    # the same problem in different words (the retrieval trap), not merely two issues sharing a log code.
    by_kb, bp = {i["kb"]: i for i in issues}, {p["code"]: p for p in prods}

    def dup_check(o: DuplicateDraft, orig: dict) -> list[str]:
        errs = []
        if o.title.strip().lower() == orig["title"].strip().lower():
            errs.append("Use a different title.")
        if orig["fixed_in"] and orig["fixed_in"] not in o.fix:
            errs.append(f"fix must name the fix release {orig['fixed_in']}.")
        if (wrong := [v for v in FIXED_IN_RE.findall(o.fix + " " + o.root_cause) if v != orig["fixed_in"]]):
            errs.append(f"The text says 'fixed in {wrong[0]}', but the fix release is {orig['fixed_in'] or 'none'}.")
        return errs

    dups = [i for i in issues if i["duplicate_of"]]
    rewrites = llm.map(lambda d: llm.generate("facts_duplicate", d["kb"], DuplicateDraft, sysmsg,
                                              P.near_duplicate(brief, bp[d["p"]], by_kb[d["duplicate_of"]]),
                                              check=lambda o: dup_check(o, by_kb[d["duplicate_of"]])), dups)
    for d, r in zip(dups, rewrites):
        orig = by_kb[d["duplicate_of"]]
        d.update({k: orig[k] for k in ("category", "code", "affected", "fixed_in", "workaround_commands")},
                 title=r.title, symptoms=r.symptoms, root_cause=r.root_cause, workaround=r.workaround, fix=r.fix,
                 twin_of=None, traps=["near_duplicate"])

    def gen_plan(p):
        kbs = [i for i in issues if i["p"] == p["code"]]
        return llm.generate("facts_guide", p["code"], GuidePlan, sysmsg, P.guide_plan(brief, p, kbs),
                            check=lambda o: validate_guide_plan(o, [i["kb"] for i in kbs], c))

    plans = llm.map(gen_plan, prods)
    glob = llm.generate("facts_global", "global", GlobalFacts, sysmsg, P.global_facts(brief), check=lambda o: validate_global(o, c))
    products = {p["code"]: {"code": p["code"], "name": p["name"], "kind": p["kind"], "versions": p["versions"],
                            "features": features[p["code"]],
                            "guide": {"id": f"GUIDE-{p['code']}", "title": gp.title,
                                      "sections": [s.model_dump() for s in gp.sections],
                                      "questions": [q.model_dump() for q in gp.questions]}}
                for p, gp in zip(prods, plans)}
    return {"vendor": brief["vendor"], "products": products, "issues": issues,
            "customers": list(dict.fromkeys(glob.customers)), "unanswerable": glob.unanswerable}


# ── Stage 2a: KB articles ───────────────────────────────────────────────────
def kb_check(b: KBBody, it: dict) -> list[str]:
    prose = "\n".join([b.summary, b.symptoms, *b.diagnosis_steps, b.sample_output, b.root_cause, *b.workaround_steps, b.resolution])
    errs = []
    if it["code"] and it["code"] not in b.sample_output:
        errs.append(f"sample_output must contain the log message {it['code']} verbatim.")
    if it["fixed_in"] and it["fixed_in"] not in b.resolution:
        errs.append(f"resolution must name the fix release {it['fixed_in']}.")
    wrong = [v for v in FIXED_IN_RE.findall(prose) if v != it["fixed_in"]]
    if wrong:
        errs.append(f"The text says 'fixed in {wrong[0]}', but the fix release is {it['fixed_in'] or 'none (no software fix)'}.")
    if ids := stray_ids(prose, [it["kb"]]):
        errs.append(f"Remove the document identifiers {ids}.")
    if not 3 <= len(b.diagnosis_steps) <= 8:
        errs.append("Give 3-6 diagnosis steps.")
    if not 300 <= (n := nwords(prose)) <= 1000:
        errs.append(f"The article is {n} words; write 450-650 words.")
    return errs


def render_kb(it: dict, prod: dict, b: KBBody) -> str:
    related = ([f"- Release notes: {rn_id(it['p'], it['fixed_in'])}"] if it["fixed_in"] else []) + [f"- Product guide: GUIDE-{it['p']}"]
    code = f"`{it['code']}`" if it["code"] else "none"
    sample = b.sample_output.replace("```", "").strip("\n")
    cmds = "\n".join(it["workaround_commands"])
    return f"""# {it['kb']}: {it['title']}

## Summary
{b.summary.strip()}

## Symptoms
{b.symptoms.strip()}

## Environment
| Item | Value |
|---|---|
| Product | {prod['name']} ({prod['kind']}) |
| Affected versions | {affected_str(it)} |
| Fixed in | {it['fixed_in'] or 'not applicable'} |
| Log message | {code} |
| Category | {it['category']} |

## Diagnosis
{numbered(b.diagnosis_steps)}

Example output:

```text
{sample}
```

## Root cause
{b.root_cause.strip()}

## Workaround
{numbered(b.workaround_steps)}

```text
{cmds}
```

## Resolution
{b.resolution.strip()}

## Related
{chr(10).join(related)}
"""


def write_kb(out: Path, llm: LLM, brief: dict, facts: dict, rng: random.Random, texts: dict) -> list[dict]:
    print("Stage 2/3: documents - KB articles")
    d = out / "kb"
    d.mkdir(parents=True)
    bp, sysmsg = {p["code"]: p for p in brief["products"]}, P.system(brief)
    updated = [date(2026, 1, 1) + timedelta(days=rng.randint(0, 320)) for _ in facts["issues"]]
    bodies = llm.map(lambda it: llm.generate("doc_kb", it["kb"], KBBody, sysmsg, P.kb(brief, bp[it["p"]], it),
                                             check=lambda b: kb_check(b, it)), facts["issues"])
    docs = []
    for it, body, upd in zip(facts["issues"], bodies, updated):
        prod = facts["products"][it["p"]]
        meta = {"doc_id": it["kb"], "doc_type": "kb", "product": prod["name"], "version_family": version_family(it),
                "affected_versions": affected_str(it), "fixed_in": it["fixed_in"] or "n/a", "category": it["category"],
                "error_code": it["code"] or "none", "last_updated": upd.isoformat()}
        text = render_kb(it, prod, body)
        write(d / f"{it['kb']}.md", front_matter(meta) + text)
        texts[it["kb"]] = text
        docs.append(meta)
    return docs


# ── Stage 2b: release notes ─────────────────────────────────────────────────
def rn_check(b: ReleaseNoteBody, feats: list[str]) -> list[str]:
    errs = []
    if len(b.features) != len(feats):
        errs.append(f"Write exactly {len(feats)} FeatureNote entries, one per feature, in order.")
    prose = "\n".join([b.overview, b.compatibility, *b.upgrade_steps, *(f.description for f in b.features)])
    if ids := stray_ids(prose):
        errs.append(f"Remove the document identifiers {ids}.")
    if not 3 <= len(b.upgrade_steps) <= 8:
        errs.append("Give 3-6 upgrade steps.")
    return errs


def write_release_notes(out: Path, llm: LLM, brief: dict, facts: dict, texts: dict) -> list[dict]:
    print("Stage 2/3: documents - release notes")
    d = out / "release_notes"
    d.mkdir(parents=True)
    bp, sysmsg = {p["code"]: p for p in brief["products"]}, P.system(brief)
    jobs = []
    for code, prod in facts["products"].items():
        for i, v in enumerate(prod["versions"]):
            fixed = [it for it in facts["issues"] if it["p"] == code and it["fixed_in"] == v]
            known = [it for it in facts["issues"] if it["p"] == code and it["affected"] != "all" and v in it["affected"]]
            jobs.append((code, prod, v, prod["versions"][i - 1] if i else None, fixed, known))

    def gen(job):
        code, prod, v, prev, fixed, known = job
        feats = prod["features"][v]
        return llm.generate("doc_release_note", rn_id(code, v), ReleaseNoteBody, sysmsg,
                            P.release_note(brief, bp[code], v, prev, feats, fixed, known), check=lambda b: rn_check(b, feats))

    bodies = llm.map(gen, jobs)
    docs = []
    for (code, prod, v, prev, fixed, known), b in zip(jobs, bodies):
        rid = rn_id(code, v)
        meta = {"doc_id": rid, "doc_type": "release_note", "product": prod["name"], "version": v,
                "version_family": ".".join(v.split(".")[:2])}
        feats = "\n\n".join(f"### {name}\n{fn.description.strip()}" for name, fn in zip(prod["features"][v], b.features))
        fixed_md = "\n".join(f"- {it['kb']}: {it['title']} ({it['code'] or 'no log message'})" for it in fixed) or "- None"
        known_md = "\n".join(f"- {it['kb']}: {it['title']}. Workaround: {it['workaround']}" for it in known) or "- None"
        path_txt = f"Supported direct upgrade path from {prev}." if prev else "Initial release in this train."
        text = f"""# {prod['name']} release {v}: release notes

## Overview
{b.overview.strip()}

## New features
{feats}

## Resolved issues
{fixed_md}

## Known issues
{known_md}

## Compatibility
{b.compatibility.strip()}

## Upgrade notes
{path_txt} Back up the configuration before upgrading and review the known issues above.

{numbered(b.upgrade_steps)}
"""
        write(d / f"{rid}.md", front_matter(meta) + text)
        texts[rid] = text
        docs.append(meta)
    return docs


# ── Stage 2c: resolved tickets ──────────────────────────────────────────────
VOICES = ["customer email to the TAC mailbox", "NOC escalation", "on-site field engineer", "phone call logged by the TAC agent",
          "partner escalation on behalf of the customer", "customer portal web form"]
SEVERITY = ["P1", "P2", "P2", "P3", "P3", "P3", "P4"]


def ticket_check(batch: TicketBatch, it: dict, specs: list[dict]) -> list[str]:
    if len(batch.tickets) != len(specs):
        return [f"Return exactly {len(specs)} tickets (got {len(batch.tickets)})."]
    errs = []
    for n, (t, s) in enumerate(zip(batch.tickets, specs), 1):
        full = " ".join([t.subject, t.description, t.resolution])
        if it["code"] and s["include_log_message"] and it["code"] not in t.description:
            errs.append(f"Ticket {n}: the description must quote {it['code']} verbatim.")
        if it["code"] and not s["include_log_message"] and it["code"] in full:
            errs.append(f"Ticket {n}: must not contain {it['code']} anywhere.")
        if it["kb"] not in t.resolution:
            errs.append(f"Ticket {n}: the resolution must cite {it['kb']}.")
        if s["resolution_path"] == "upgrade" and it["fixed_in"] not in t.resolution:
            errs.append(f"Ticket {n}: the resolution must say the customer upgraded to {it['fixed_in']}.")
        if s["version"] not in t.description:
            errs.append(f"Ticket {n}: the description must mention the running version {s['version']}.")
        if len(t.description.split()) < 30:
            errs.append(f"Ticket {n}: the description is too short; write 3-6 sentences.")
        if ids := stray_ids(full, [it["kb"]]):
            errs.append(f"Ticket {n}: remove document identifiers {ids}.")
    return errs


def howto_check(batch: TicketBatch, gid: str, n_specs: int) -> list[str]:
    if len(batch.tickets) != n_specs:
        return [f"Return exactly {n_specs} tickets (got {len(batch.tickets)})."]
    errs = []
    for n, t in enumerate(batch.tickets, 1):
        if gid not in t.resolution:
            errs.append(f"Ticket {n}: the resolution must contain {gid}.")
        if len(t.description.split()) < 30:
            errs.append(f"Ticket {n}: the description is too short; write 3-6 sentences.")
        if ids := stray_ids(" ".join([t.subject, t.description, t.resolution]), [gid]):
            errs.append(f"Ticket {n}: remove document identifiers {ids}.")
    return errs


def write_tickets(out: Path, llm: LLM, brief: dict, facts: dict, rng: random.Random, texts: dict) -> list[dict]:
    print("Stage 2/3: documents - resolved tickets")
    d = out / "tickets"
    d.mkdir(parents=True)
    bp, sysmsg, c, prods = {p["code"]: p for p in brief["products"]}, P.system(brief), brief["counts"], facts["products"]
    customers = facts["customers"]
    public = lambda s: {k: v for k, v in s.items() if not k.startswith("_")}

    # issue tickets: every random choice is drawn up front so prompts (and the cache) are deterministic
    jobs = []
    for it in [i for i in facts["issues"] if i["q"] is not None]:       # near-duplicate KBs are not referenced by tickets
        versions = prods[it["p"]]["versions"] if it["affected"] == "all" else it["affected"]
        specs = []
        for n in range(c["tickets_per_issue"]):
            opened = date(2026, 1, 5) + timedelta(days=rng.randint(0, 310))
            specs.append({"ticket": n + 1, "customer": rng.choice(customers), "version": rng.choice(versions),
                          "severity": rng.choice(SEVERITY), "voice": rng.choice(VOICES),
                          "include_log_message": bool(it["code"]) and rng.random() < 0.6,
                          "resolution_path": "upgrade" if it["fixed_in"] and rng.random() < 0.4 else "workaround",
                          "_opened": opened, "_closed": opened + timedelta(days=rng.randint(1, 14))})
        jobs.append((it, specs))
    batches = llm.map(lambda j: llm.generate("doc_tickets", j[0]["kb"], TicketBatch, sysmsg,
                                             P.tickets(brief, bp[j[0]["p"]], j[0], [public(s) for s in j[1]]),
                                             check=lambda b: ticket_check(b, j[0], j[1])), jobs)

    # how-to tickets resolved from the product guides
    gq = [(code, q) for code, prod in prods.items() for q in prod["guide"]["questions"]]
    howto: dict[str, list[dict]] = {}
    for i in range(c["how_to_tickets"]):
        code, q = gq[i % len(gq)]
        sec = prods[code]["guide"]["sections"][q["section_index"]]
        opened = date(2026, 1, 5) + timedelta(days=rng.randint(0, 310))
        howto.setdefault(code, []).append({"ticket": len(howto.get(code, [])) + 1, "customer": rng.choice(customers),
                                           "version": rng.choice(prods[code]["versions"]), "question": q["question"],
                                           "answer_from_guide": sec["key_facts"] + sec["commands"],
                                           "_opened": opened, "_closed": opened + timedelta(days=rng.randint(1, 5))})
    hjobs = list(howto.items())
    hbatches = llm.map(lambda j: llm.generate("doc_tickets_howto", f"GUIDE-{j[0]}", TicketBatch, sysmsg,
                                              P.howto_tickets(brief, bp[j[0]], f"GUIDE-{j[0]}", [public(s) for s in j[1]]),
                                              check=lambda b: howto_check(b, f"GUIDE-{j[0]}", len(j[1]))), hjobs)

    tickets, n = [], 50001
    for (it, specs), batch in zip(jobs, batches):
        for s, t in zip(specs, batch.tickets):
            full = " ".join([t.subject, t.description, t.resolution])
            tickets.append({"ticket_id": f"TKT-{n}", "doc_type": "ticket", "customer": s["customer"],
                            "product": prods[it["p"]]["name"], "version": s["version"], "severity": s["severity"],
                            "opened": s["_opened"].isoformat(), "closed": s["_closed"].isoformat(),
                            "subject": t.subject.strip(), "description": t.description.strip(), "resolution": t.resolution.strip(),
                            "kb_refs": [it["kb"]], "error_code": it["code"] if it["code"] and it["code"] in full else ""})
            n += 1
    for (code, specs), batch in zip(hjobs, hbatches):
        for s, t in zip(specs, batch.tickets):
            tickets.append({"ticket_id": f"TKT-{n}", "doc_type": "ticket", "customer": s["customer"],
                            "product": prods[code]["name"], "version": s["version"], "severity": "P4",
                            "opened": s["_opened"].isoformat(), "closed": s["_closed"].isoformat(),
                            "subject": t.subject.strip(), "description": t.description.strip(), "resolution": t.resolution.strip(),
                            "kb_refs": [], "error_code": ""})
            n += 1
    rng.shuffle(tickets)
    for t in tickets:
        texts[t["ticket_id"]] = f"{t['subject']}\n{t['description']}\nResolution: {t['resolution']}"
    write(d / "resolved_tickets.json", json.dumps(tickets, indent=2, ensure_ascii=False) + "\n")
    return tickets


# ── Stage 2d: product guides (PDF) ──────────────────────────────────────────
PDF_SAFE = str.maketrans({"→": "->", "←": "<-", "≤": "<=", "≥": ">=", "≈": "~", "−": "-", "‑": "-", "‐": "-",
                          " ": " ", " ": " ", " ": " ", "✓": "OK", "µ": "u", "Δ": "delta"})


def guide_section_check(b: GuideSectionBody) -> list[str]:
    errs = []
    prose = "\n".join([*b.paragraphs, *b.procedure_steps, b.verification])
    if ids := stray_ids(prose):
        errs.append(f"Remove the document identifiers {ids}.")
    if not 4 <= len(b.paragraphs) <= 8:
        errs.append("Write 4-7 paragraphs.")
    if not 300 <= (n := nwords(*b.paragraphs)) <= 900:
        errs.append(f"The paragraphs total {n} words; write 400-650 words.")
    if b.table and (not b.table.rows or any(len(r) != len(b.table.header) for r in b.table.rows)):
        errs.append("Every table row must have exactly as many cells as the header.")
    return errs


def render_guide(path: Path, vendor: dict, prod: dict, guide: dict, front: GuideFront,
                 bodies: list[GuideSectionBody], issues: list[dict]):
    from reportlab import rl_config
    rl_config.invariant = 1                                   # deterministic PDF bytes
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, ListFlowable, ListItem, NextPageTemplate, PageBreak,
                                    PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle)
    from reportlab.platypus.tableofcontents import TableOfContents

    accent, rule, shade = colors.HexColor("#1F4E79"), colors.HexColor("#C8D0DA"), colors.HexColor("#F2F4F7")
    ss = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=ss["Normal"], fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
    h1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=16, leading=20, textColor=accent, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=11.5, leading=15, textColor=accent, spaceBefore=8, spaceAfter=4)
    toc_head = ParagraphStyle("TOCHead", parent=h1)
    code = ParagraphStyle("CodeBlock", parent=ss["Code"], fontSize=8.5, leading=11, backColor=shade, borderColor=rule,
                          borderWidth=0.5, borderPadding=6, leftIndent=6, rightIndent=6, spaceBefore=6, spaceAfter=12)
    cell = ParagraphStyle("Cell", parent=ss["Normal"], fontSize=8.5, leading=11)
    cell_code = ParagraphStyle("CellCode", parent=cell, fontName="Courier", fontSize=8)
    caption = ParagraphStyle("Caption", parent=cell, fontName="Helvetica-Oblique", textColor=colors.grey, spaceBefore=4, spaceAfter=4)
    cover_t = ParagraphStyle("CoverTitle", parent=ss["Title"], fontSize=26, leading=32, textColor=accent, alignment=0)
    cover_s = ParagraphStyle("CoverSub", parent=ss["Normal"], fontSize=13, leading=18, textColor=colors.HexColor("#344054"))

    def t(s: str) -> str:
        return escape(str(s).translate(PDF_SAFE).strip())

    def para(s: str, style=body):
        return [Paragraph(t(p), style) for p in str(s).split("\n\n") if p.strip()]

    def bullets(items, numbered_list=False):
        return ListFlowable([ListItem(Paragraph(t(i), body), leftIndent=14) for i in items],
                            bulletType="1" if numbered_list else "bullet", start=None if numbered_list else "•",
                            leftIndent=14, bulletFontSize=9)

    def table(header, rows, widths, code_cols=()):
        n = len(header)
        data = [[Paragraph(f"<b>{t(h)}</b>", cell) for h in header]]
        data += [[Paragraph(t(v), cell_code if j in code_cols else cell) for j, v in enumerate((list(r) + [""] * n)[:n])] for r in rows]
        tbl = Table(data, colWidths=widths, repeatRows=1)
        tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")), ("GRID", (0, 0), (-1, -1), 0.4, rule),
                                 ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return tbl

    class GuideDoc(BaseDocTemplate):
        def __init__(self, filename, **kw):
            super().__init__(filename, **kw)
            frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
            self.addPageTemplates([PageTemplate("cover", [frame]), PageTemplate("page", [frame], onPage=self.decorate)])

        def decorate(self, c, _doc):
            w, h = A4
            c.saveState()
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.grey)
            c.setStrokeColor(rule)
            c.drawString(self.leftMargin, h - 1.3 * cm, guide["title"].translate(PDF_SAFE))
            c.drawRightString(w - self.rightMargin, h - 1.3 * cm, vendor["name"])
            c.line(self.leftMargin, h - 1.45 * cm, w - self.rightMargin, h - 1.45 * cm)
            c.line(self.leftMargin, 1.55 * cm, w - self.rightMargin, 1.55 * cm)
            c.drawString(self.leftMargin, 1.1 * cm, f"{guide['id']}  |  {prod['name']}")
            c.drawRightString(w - self.rightMargin, 1.1 * cm, f"Page {c.getPageNumber()}")
            c.restoreState()

        def afterFlowable(self, f):
            if isinstance(f, Paragraph) and f.style.name == "H1":
                self.notify("TOCEntry", (0, f.getPlainText(), self.page))

    doc = GuideDoc(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.2 * cm, bottomMargin=2.2 * cm,
                   title=guide["title"], author=f"{vendor['name']} Technical Documentation", subject=prod["name"])
    width = doc.width
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("TOC1", parent=body, fontSize=10.5, leading=16, leftIndent=0, alignment=0)]

    story = [Spacer(1, 4 * cm), Paragraph(t(vendor["name"]).upper(), cover_s), Spacer(1, 0.6 * cm),
             Paragraph(t(guide["title"]), cover_t), Spacer(1, 0.4 * cm),
             Paragraph(t(f"{prod['name']} {prod['kind']}"), cover_s), Spacer(1, 3 * cm),
             Paragraph(t(f"Document {guide['id']}"), body),
             Paragraph(t(f"Applies to releases {', '.join(prod['versions'])}"), body),
             Paragraph("Revision: November 2026", body),
             NextPageTemplate("page"), PageBreak(),
             Paragraph("Contents", toc_head), toc, PageBreak(),
             Paragraph("1. About this guide", h1), *para(front.about),
             Paragraph("Audience", h2), *para(front.audience),
             Paragraph("Documentation conventions", h2), bullets(front.conventions),
             Paragraph("Related documentation", h2),
             *para(f"This guide complements the {prod['name']} knowledge-base articles and release notes, which describe "
                   "specific defects, workarounds and fixes. Appendix A maps log messages to knowledge-base articles."),
             PageBreak()]
    n = 1
    for sec, b in zip(guide["sections"], bodies):
        n += 1
        story += [Paragraph(t(f"{n}. {sec['heading']}"), h1), *[x for p in b.paragraphs for x in para(p)],
                  Paragraph("Recommendations", h2), bullets(sec["key_facts"]),
                  Paragraph("Configuration procedure", h2), bullets(b.procedure_steps, numbered_list=True),
                  KeepTogether([Paragraph("Configuration example", h2), Preformatted("\n".join(sec["commands"]), code)])]
        if b.table:
            k = len(b.table.header)
            story += [Spacer(1, 4), table(b.table.header, b.table.rows, [width / k] * k), Paragraph(t(b.table.caption), caption)]
        story += [Paragraph("Verification", h2), *para(b.verification), PageBreak()]
    n += 1
    story += [Paragraph(f"{n}. Software upgrades", h1),
              *para(f"Supported releases: {', '.join(prod['versions'])}. Always read the release notes for the target release, "
                    "back up the configuration, verify the image checksum, and upgrade during a maintenance window. "
                    "Upgrade redundant or stacked systems one member at a time and confirm that the member rejoins before "
                    "continuing. Review the known issues listed in the release notes of the target release."),
              Paragraph("Release highlights", h2),
              table(["Release", "Highlights"], [[v, "; ".join(prod["features"][v])] for v in prod["versions"]], [2.5 * cm, width - 2.5 * cm]),
              PageBreak(),
              Paragraph("Appendix A. Log message reference", h1),
              *para("The following log messages are associated with known issues. Search the knowledge base for the "
                    "article number for symptoms, workaround and resolution.")]
    rows = [[it["code"], it["title"], it["kb"]] for it in sorted(issues, key=lambda i: (i["code"] or "", i["kb"])) if it["code"]]
    story.append(table(["Log message", "Description", "KB article"], rows, [6 * cm, width - 8.2 * cm, 2.2 * cm], code_cols=(0,)))
    doc.multiBuild(story)


def write_guides(out: Path, llm: LLM, brief: dict, facts: dict, texts: dict) -> list[dict]:
    print("Stage 2/3: documents - product guides (PDF)")
    from pypdf import PdfReader

    d = out / "guides"
    d.mkdir(parents=True)
    bp, sysmsg, prods = {p["code"]: p for p in brief["products"]}, P.system(brief), facts["products"]
    codes = list(prods)
    fronts = llm.map(lambda code: llm.generate("doc_guide_front", f"GUIDE-{code}", GuideFront, sysmsg,
                                               P.guide_front(brief, bp[code], prods[code]["guide"])), codes)
    jobs = [(code, i, sec) for code in codes for i, sec in enumerate(prods[code]["guide"]["sections"])]
    bodies = llm.map(lambda j: llm.generate("doc_guide_section", f"GUIDE-{j[0]}#{j[1] + 1}", GuideSectionBody, sysmsg,
                                            P.guide_section(brief, bp[j[0]], prods[j[0]]["guide"], j[2]),
                                            check=guide_section_check), jobs)
    docs = []
    for code, front in zip(codes, fronts):
        guide = prods[code]["guide"]
        path = d / f"{guide['id']}.pdf"
        secs = [b for (c, _, _), b in zip(jobs, bodies) if c == code]
        render_guide(path, facts["vendor"], prods[code], guide, front, secs, [i for i in facts["issues"] if i["p"] == code])
        texts[guide["id"]] = " ".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        docs.append({"doc_id": guide["id"], "doc_type": "guide", "product": prods[code]["name"]})
    return docs


# ── Stage 3: golden evaluation set ──────────────────────────────────────────
TYPE_RANK = {"KB": 0, "TKT": 1, "RN": 2, "GUIDE": 3}
NOT_FOUND = "The knowledge base does not contain this information."


def write_golden(out: Path, llm: LLM, brief: dict, facts: dict, tickets: list[dict], texts: dict, rng: random.Random) -> list[dict]:
    print("Stage 3/3: golden evaluation set")
    d = out / "eval"
    d.mkdir(parents=True)
    g, issues, prods, sysmsg = brief["golden"], facts["issues"], facts["products"], P.system(brief)
    name = lambda it: prods[it["p"]]["name"]
    view = lambda it: {"product": name(it), **{k: it[k] for k in ["kb", "code", "title", "symptoms", "root_cause", "workaround",
                                                                  "workaround_commands", "fix", "affected", "fixed_in"]}}
    specs: list[dict] = []

    def add(qtype, label, expected, facts_, instruction, question=None, filters=None, must=(), must_not=(), answer_must=()):
        specs.append(dict(type=qtype, label=label, expected=expected, facts=facts_, instruction=instruction, question=question,
                          filters=filters or {}, must=list(must), must_not=[m for m in must_not if m], answer_must=[a for a in answer_must if a]))

    fixed_q = "The question is fixed; set 'question' to exactly this text: "
    twins = [it for it in issues if "version_twin" in it["traps"]]
    singles = [it for it in issues if it["q"] and "version_twin" not in it["traps"]]
    rng.shuffle(singles)
    for it in sorted(singles[:g["single_hop"]], key=lambda x: x["kb"]):
        exp = [it["kb"]] + [o["kb"] for o in issues if o is not it and it["code"] and o["code"] == it["code"]]
        add("single_hop", it["kb"], exp, view(it), fixed_q + it["q"], question=it["q"], answer_must=[it["fixed_in"]])
    for it in twins[:g["version_specific"]]:
        v = next((x for x in it["affected"] if x in it["q"]), it["affected"][-1])
        exp = [it["kb"]] + [o["kb"] for o in issues if o["duplicate_of"] == it["kb"]]     # a near-duplicate is equally valid
        add("version_specific", it["kb"], exp, view(it), fixed_q + it["q"], question=it["q"],
            filters={"product": name(it), "version": v}, answer_must=[it["fixed_in"]])

    codes = sorted({it["code"] for it in issues if it["code"]})
    shared = [c for c in codes if sum(o["code"] == c for o in issues) > 1]
    others = [c for c in codes if c not in shared]
    for code in (shared + rng.sample(others, max(0, min(len(others), g["error_code"] - len(shared)))))[:g["error_code"]]:
        hits = [it for it in issues if it["code"] == code]
        # Any document that literally contains the code is valid evidence: KB article(s), tickets that logged it,
        # release notes that list it as fixed, and the guide's log-message appendix.
        evidence = sorted((i for i, txt in texts.items() if code in txt), key=lambda i: (TYPE_RANK[i.split("-")[0]], i))
        add("error_code", code, evidence, view(hits[0]),
            f"Write the question an engineer would ask after finding {code} in the logs: what it means and what to do. "
            f"The question must contain {code} verbatim.", must=[code])

    cands = [it for it in issues if it["fixed_in"] and it["q"]]
    for it in sorted(rng.sample(cands, min(g["multi_hop"], len(cands))), key=lambda x: x["kb"]):
        v = it["affected"][-1]
        add("multi_hop", it["kb"], [it["kb"], rn_id(it["p"], it["fixed_in"])], view(it),
            f"A customer running {name(it)} {v} hits this issue. Write their question: describe the symptom in their own "
            f"words (no KB number, no log message), mention '{v}', and ask which release fixes it and what to do until they "
            "can upgrade. The answer names the fix release and the interim workaround.",
            filters={"product": name(it), "version": v}, must=[v], must_not=[it["kb"], it["code"]], answer_must=[it["fixed_in"]])

    gqs = [(code, i, q) for code, prod in prods.items() for i, q in enumerate(prod["guide"]["questions"])]
    for code, i, q in sorted(rng.sample(gqs, min(g["how_to"], len(gqs))), key=lambda x: (x[0], x[1])):
        sec = prods[code]["guide"]["sections"][q["section_index"]]
        add("how_to", f"GUIDE-{code}#{i + 1}", [f"GUIDE-{code}"] + q["related_kbs"],
            {"product": prods[code]["name"], "guide_section": sec["heading"], "recommendations": sec["key_facts"], "commands": sec["commands"]},
            fixed_q + q["question"], question=q["question"])

    tk_by_kb: dict[str, list[str]] = {}
    for tk in tickets:
        for r in tk["kb_refs"]:
            tk_by_kb.setdefault(r, []).append(tk["ticket_id"])
    cands = [it for it in issues if it["kb"] in tk_by_kb and "version_twin" not in it["traps"]]
    for it in sorted(rng.sample(cands, min(g["similar_case"], len(cands))), key=lambda x: x["kb"]):
        tids = sorted(tk_by_kb[it["kb"]])
        res = [tk["resolution"] for tk in tickets if tk["ticket_id"] in tids]
        add("similar_case", it["kb"], tids + [it["kb"]], {**view(it), "resolved_ticket_count": len(tids), "ticket_resolutions": res},
            "Write a question in which an engineer describes the symptom in their own words and asks whether other customers "
            "have reported it before and how it was resolved. No KB number and no log message in the question. The answer "
            "says how many similar resolved cases exist and how they were resolved.",
            must_not=[it["kb"], it["code"]])

    def phrase(s):
        def check(o: GoldenPhrasing) -> list[str]:
            errs = []
            if s["question"] is None:
                errs += [f"The question must contain '{m}' verbatim." for m in s["must"] if m not in o.question]
                errs += [f"The question must not contain '{m}'." for m in s["must_not"] if m in o.question]
                if ids := stray_ids(o.question):
                    errs.append(f"Remove document identifiers {ids} from the question.")
            errs += [f"The reference answer must mention '{a}'." for a in s["answer_must"] if a not in o.reference_answer]
            return errs
        return llm.generate("golden", f"{s['type']}:{s['label']}", GoldenPhrasing, sysmsg,
                            P.golden(s["type"], s["facts"], s["instruction"]), check=check)

    phrasings = llm.map(phrase, specs)
    items = []
    for s, ph in zip(specs, phrasings):
        items.append({"id": f"Q{len(items) + 1:02d}", "type": s["type"], "question": s["question"] or ph.question.strip(),
                      "expected_doc_ids": s["expected"], "reference_answer": ph.reference_answer.strip(), "filters": s["filters"]})
    for q in facts["unanswerable"][:g["unanswerable"]]:
        items.append({"id": f"Q{len(items) + 1:02d}", "type": "unanswerable", "question": q,
                      "expected_doc_ids": [], "reference_answer": NOT_FOUND, "filters": {}})
    write(d / "golden_set.json", json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    return items


# ── main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "data"), help="output directory (default: ./data)")
    ap.add_argument("--brief", default=str(SCRIPTS / "corpus_brief.toml"), help="domain brief (TOML)")
    ap.add_argument("--seed", type=int, default=SEED)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="use only scripts/llm_cache; fail on a cache miss")
    mode.add_argument("--refresh", action="store_true", help="ignore the cache and regenerate everything with the LLM")
    ap.add_argument("--issues-per-product", type=int, help="override counts.issues_per_product")
    ap.add_argument("--tickets-per-issue", type=int, help="override counts.tickets_per_issue")
    ap.add_argument("--workers", type=int, default=8, help="concurrent LLM calls (default 8)")
    ap.add_argument("--prune-cache", action="store_true", help="after a successful run, delete cache entries this run did not use")
    args = ap.parse_args()

    brief = tomllib.loads(Path(args.brief).read_text(encoding="utf-8"))
    if args.issues_per_product:
        brief["counts"]["issues_per_product"] = args.issues_per_product
    if args.tickets_per_issue:
        brief["counts"]["tickets_per_issue"] = args.tickets_per_issue
    llm = LLM(mode="offline" if args.offline else "refresh" if args.refresh else "default", workers=args.workers)
    print(f"Model: {llm.model}   cache: {SCRIPTS / 'llm_cache'}   mode: {llm.mode}")

    out = Path(args.out)
    tmp = out.with_name(out.name + ".partial")                # build aside; replace ./data only on success
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    rng = random.Random(args.seed)
    texts: dict[str, str] = {}
    try:
        facts = build_facts(llm, brief)
        write(tmp / "facts.json", json.dumps(facts, indent=2, ensure_ascii=False) + "\n")
        kb = write_kb(tmp, llm, brief, facts, rng, texts)
        rn = write_release_notes(tmp, llm, brief, facts, texts)
        tk = write_tickets(tmp, llm, brief, facts, rng, texts)
        gd = write_guides(tmp, llm, brief, facts, texts)
        gs = write_golden(tmp, llm, brief, facts, tk, texts, rng)
    except CacheMiss as e:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(f"error: {e}")

    manifest = {"seed": args.seed, "brief": Path(args.brief).name,
                "counts": {"kb": len(kb), "release_notes": len(rn), "tickets": len(tk), "guides": len(gd), "golden_questions": len(gs)},
                "golden_types": {t: sum(1 for g in gs if g["type"] == t) for t in dict.fromkeys(g["type"] for g in gs)},
                "traps": {"version_twin_issues": sum("version_twin" in i["traps"] for i in facts["issues"]),
                          "near_duplicate_issues": sum("near_duplicate" in i["traps"] for i in facts["issues"])}}
    write(tmp / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    if out.exists():
        shutil.rmtree(out)
    tmp.rename(out)

    print(f"\nCorpus written to {out}")
    for k, v in manifest["counts"].items():
        print(f"  {k:17s} {v}")
    print("  golden types     ", manifest["golden_types"])
    if args.prune_cache:
        print(f"  pruned            {llm.prune()} unused cache files")
    print(f"  LLM calls         {llm.stats['generated']} generated, {llm.stats['cached']} from cache, {llm.stats['retries']} rejected attempts")


if __name__ == "__main__":
    main()
