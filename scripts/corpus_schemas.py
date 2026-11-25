"""Pydantic schemas for the LLM-generated corpus.

Two kinds of models live here:

* LLM output models (``*Draft``, ``*Body``, ...): what the LLM must return through
  structured output. They have no defaults, because OpenAI strict JSON-schema mode
  requires every field.
* ``validate_*`` functions: deterministic checks of the cross-field rules that a
  JSON schema cannot express (version ranges, trap pairs, ...). They return a list
  of human-readable errors that are fed back to the LLM on retry.
"""

import re

from pydantic import BaseModel, Field

CODE_RE = re.compile(r"^(%[A-Z0-9_]+-[0-7]-[A-Z0-9_][A-Z0-9_-]*[A-Z0-9_]|ERR-[A-Z0-9]+-\d{3,5})$")


def vkey(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def family(v: str) -> str:
    return ".".join(v.split(".")[:2])


# ── Stage 1: facts ──────────────────────────────────────────────────────────
class IssueDraft(BaseModel):
    ref: str = Field(description="Local reference, I01, I02, ... in order.")
    category: str = Field(description="Short area, e.g. Routing, VPN, Roaming, Stacking, Performance, Software.")
    error_code: str | None = Field(description="Log message that identifies the issue, or null if none is logged.")
    title: str = Field(description="KB article title, specific and technical (mentions the version train where relevant).")
    symptoms: str = Field(description="2-3 sentences: what the customer observes, with concrete numbers.")
    root_cause: str = Field(description="2-3 sentences: precise technical root cause.")
    workaround: str = Field(description="1-2 sentences: what to do now, with concrete values.")
    workaround_commands: list[str] = Field(description="1-3 exact CLI commands that implement the workaround.")
    fix: str = Field(description="One sentence: 'Fixed in X: ...' or 'No software fix required; ...'.")
    affects_all_versions: bool = Field(description="True only for configuration/design issues that affect every release.")
    affected_versions: list[str] = Field(description="Affected releases (empty when affects_all_versions is true).")
    fixed_in: str | None = Field(description="Release that fixes it, or null for configuration issues.")
    engineer_question: str | None = Field(description="How a field engineer would ask about it, worded differently from the title. Null only for the duplicate of a near-duplicate pair.")
    twin_of: str | None = Field(description="ref of this issue's version-twin partner, or null.")
    duplicate_of: str | None = Field(description="ref of the issue this one near-duplicates (same error code), or null.")


class ReleaseFeatures(BaseModel):
    version: str
    features: list[str] = Field(description="1-3 short feature or improvement names for this release.")


class ProductIssues(BaseModel):
    issues: list[IssueDraft]
    releases: list[ReleaseFeatures]


class DuplicateDraft(BaseModel):
    title: str = Field(description="A different title for the same problem.")
    symptoms: str
    root_cause: str
    workaround: str
    fix: str


class GuideSectionPlan(BaseModel):
    heading: str
    key_facts: list[str] = Field(description="2-4 specific recommendations with concrete values, each one full sentence.")
    commands: list[str] = Field(description="2-5 exact CLI commands that implement the recommendations.")
    related_kbs: list[str] = Field(description="KB IDs (from the list given) that this section helps prevent or diagnose; may be empty.")


class GuideQuestionPlan(BaseModel):
    question: str = Field(description="A how-to question an engineer would ask, answered by one section.")
    section_index: int = Field(description="0-based index of the section that answers it.")
    related_kbs: list[str] = Field(description="0-2 KB IDs that would also be useful evidence.")


class GuidePlan(BaseModel):
    title: str
    sections: list[GuideSectionPlan]
    questions: list[GuideQuestionPlan]


class GlobalFacts(BaseModel):
    customers: list[str] = Field(description="Fictional enterprise customer names (company names only).")
    unanswerable: list[str] = Field(description="Plausible questions the knowledge base does NOT answer (pricing, roadmap, third-party integrations, competitors, ...).")


# ── Stage 2: document prose ────────────────────────────────────────────────
class KBBody(BaseModel):
    summary: str = Field(description="2-3 sentence overview for the top of the article.")
    symptoms: str = Field(description="One or two paragraphs describing what is observed.")
    diagnosis_steps: list[str] = Field(description="3-6 ordered diagnostic steps, each naming the command or check and what to look for.")
    sample_output: str = Field(description="Realistic multi-line log and/or CLI output that confirms the issue.")
    root_cause: str = Field(description="One or two paragraphs explaining the root cause.")
    workaround_steps: list[str] = Field(description="2-5 ordered steps to apply the workaround.")
    resolution: str = Field(description="One paragraph: permanent resolution.")


class FeatureNote(BaseModel):
    name: str
    description: str = Field(description="2-4 sentences describing the feature and its configuration impact.")


class ReleaseNoteBody(BaseModel):
    overview: str = Field(description="One paragraph summarising the release.")
    features: list[FeatureNote]
    compatibility: str = Field(description="One paragraph on hardware, interoperability and configuration compatibility.")
    upgrade_steps: list[str] = Field(description="3-6 ordered upgrade steps.")


class TicketDraft(BaseModel):
    subject: str = Field(description="Short ticket subject line as a customer or engineer would type it.")
    description: str = Field(description="The customer's report plus initial triage notes, 3-6 sentences.")
    resolution: str = Field(description="How TAC resolved it, 2-4 sentences.")


class TicketBatch(BaseModel):
    tickets: list[TicketDraft]


class GuideTable(BaseModel):
    caption: str
    header: list[str]
    rows: list[list[str]]


class GuideFront(BaseModel):
    about: str = Field(description="One or two paragraphs: purpose and scope of the guide.")
    audience: str = Field(description="One paragraph: intended audience and prerequisites.")
    conventions: list[str] = Field(description="3-5 documentation conventions (command syntax, notes, warnings).")


class GuideSectionBody(BaseModel):
    paragraphs: list[str] = Field(description="4-7 paragraphs of explanatory text.")
    procedure_steps: list[str] = Field(description="3-7 ordered configuration steps.")
    table: GuideTable | None = Field(description="Optional parameter/reference table, or null.")
    verification: str = Field(description="One paragraph on how to verify the configuration.")


class GoldenPhrasing(BaseModel):
    question: str
    reference_answer: str = Field(description="2-4 sentences answering the question using only the facts given.")


# ── deterministic validation ────────────────────────────────────────────────
def validate_product_issues(pi: ProductIssues, versions: list[str], counts: dict, traps: dict) -> list[str]:
    errs: list[str] = []
    n = counts["issues_per_product"]
    if len(pi.issues) != n:
        errs.append(f"Return exactly {n} issues (got {len(pi.issues)}).")
    refs = [i.ref for i in pi.issues]
    if len(set(refs)) != len(refs):
        errs.append("Issue refs must be unique.")
    by_ref = {i.ref: i for i in pi.issues}
    for it in pi.issues:
        tag = f"{it.ref}:"
        if it.error_code is not None and not CODE_RE.match(it.error_code):
            errs.append(f"{tag} error_code '{it.error_code}' does not match %FACILITY-SEV-MNEMONIC or ERR-AREA-NNNN.")
        if not it.workaround_commands:
            errs.append(f"{tag} needs at least one workaround command.")
        if it.affects_all_versions:
            if it.affected_versions:
                errs.append(f"{tag} affects_all_versions is true, so affected_versions must be empty.")
            if it.fixed_in is not None:
                errs.append(f"{tag} issues affecting all versions are configuration issues: fixed_in must be null.")
        else:
            bad = [v for v in it.affected_versions if v not in versions]
            if not it.affected_versions:
                errs.append(f"{tag} affected_versions is empty but affects_all_versions is false.")
            elif bad:
                errs.append(f"{tag} unknown versions {bad}; allowed: {versions}.")
            elif len({family(v) for v in it.affected_versions}) != 1:
                errs.append(f"{tag} affected_versions {it.affected_versions} span several version families; "
                            "they must all share the same major.minor family.")
        if it.fixed_in is not None:
            if it.fixed_in not in versions:
                errs.append(f"{tag} fixed_in '{it.fixed_in}' is not a release; allowed: {versions}.")
            elif it.affected_versions and any(v in versions and vkey(v) >= vkey(it.fixed_in) for v in it.affected_versions):
                errs.append(f"{tag} fixed_in {it.fixed_in} must be newer than every affected version {it.affected_versions}.")
        if it.duplicate_of is None and not it.engineer_question:
            errs.append(f"{tag} engineer_question is required (only a near-duplicate's second article may omit it).")
    # version twins
    pairs = {frozenset((i.ref, i.twin_of)) for i in pi.issues if i.twin_of}
    nt = traps["version_twin_pairs_per_product"]
    if not nt <= len(pairs) <= nt + 1:
        errs.append(f"Mark {nt} version-twin pair(s) with twin_of (got {len(pairs)} pairs). Both twins point at each other; "
                    "no issue may be in two pairs.")
    if any(sum(i.ref in pr for pr in pairs) > 1 for i in pi.issues):
        errs.append("An issue may belong to only one version-twin pair.")
    for pair in pairs:
        a, b = (by_ref.get(r) for r in sorted(pair))
        if not a or not b or a is b:
            errs.append(f"twin_of {sorted(pair)} must reference two different existing issues.")
            continue
        if a.affects_all_versions or b.affects_all_versions or not a.affected_versions or not b.affected_versions:
            errs.append(f"Twins {a.ref}/{b.ref} must each affect specific versions, not all versions.")
            continue
        if family(a.affected_versions[0]) == family(b.affected_versions[0]):
            errs.append(f"Twins {a.ref}/{b.ref} must affect different version families.")
        for t in (a, b):
            if t.engineer_question and not any(v in t.engineer_question for v in t.affected_versions):
                errs.append(f"{t.ref}: a version twin's engineer_question must mention one of its affected versions {t.affected_versions}.")
    # near duplicates
    dups = [i for i in pi.issues if i.duplicate_of]
    nd = traps["near_duplicate_pairs_per_product"]
    if not nd <= len(dups) <= nd + 1:
        errs.append(f"Mark {nd} near-duplicate article(s) with duplicate_of (got {len(dups)}). Set duplicate_of only on the "
                    "second article of a pair, never on both.")
    for d in dups:
        o = by_ref.get(d.duplicate_of)
        if not o or o is d:
            errs.append(f"{d.ref}: duplicate_of must reference another existing issue.")
        elif not d.error_code or d.error_code != o.error_code:
            errs.append(f"{d.ref}: a near-duplicate must have the same non-null error_code as {o.ref}.")
        elif d.twin_of or any(i.twin_of == d.ref for i in pi.issues):
            errs.append(f"{d.ref}: the second article of a near-duplicate pair must not also be a version twin.")
    # a log message may be shared by at most two issues (near-duplicates, or genuinely related problems)
    for code in {i.error_code for i in pi.issues if i.error_code}:
        if sum(i.error_code == code for i in pi.issues) > 2:
            errs.append(f"error_code {code} is used by more than two issues.")
    fixed = sum(1 for i in pi.issues if i.fixed_in)
    if fixed < counts["min_fixed_issues_per_product"]:
        errs.append(f"At least {counts['min_fixed_issues_per_product']} issues need a software fix (fixed_in); got {fixed}.")
    # release features
    rel = {r.version for r in pi.releases}
    if rel != set(versions) or len(pi.releases) != len(versions):
        errs.append(f"releases must contain exactly one entry per version {versions}.")
    if any(not r.features for r in pi.releases):
        errs.append("Every release needs at least one feature.")
    return errs


def validate_guide_plan(gp: GuidePlan, kb_ids: list[str], counts: dict) -> list[str]:
    errs = []
    if len(gp.sections) != counts["guide_sections"]:
        errs.append(f"Return exactly {counts['guide_sections']} sections (got {len(gp.sections)}).")
    for i, s in enumerate(gp.sections):
        if len(s.key_facts) < 2 or len(s.commands) < 2:
            errs.append(f"Section {i} needs at least 2 key_facts and 2 commands.")
        bad = [k for k in s.related_kbs if k not in kb_ids]
        if bad:
            errs.append(f"Section {i}: unknown KB IDs {bad}.")
    if len(gp.questions) != counts["guide_questions_per_product"]:
        errs.append(f"Return exactly {counts['guide_questions_per_product']} questions.")
    for q in gp.questions:
        if not 0 <= q.section_index < len(gp.sections):
            errs.append(f"Question '{q.question[:40]}...' has invalid section_index {q.section_index}.")
        bad = [k for k in q.related_kbs if k not in kb_ids]
        if bad or len(q.related_kbs) > 2:
            errs.append(f"Question '{q.question[:40]}...': related_kbs must be 0-2 IDs from the list (bad: {bad}).")
    if len({q.section_index for q in gp.questions}) != len(gp.questions):
        errs.append("Each question must be answered by a different section.")
    return errs


def validate_global(g: GlobalFacts, counts: dict) -> list[str]:
    errs = []
    if len(set(g.customers)) != counts["customers"]:
        errs.append(f"Return exactly {counts['customers']} distinct customer names.")
    if len(g.unanswerable) != counts["unanswerable"]:
        errs.append(f"Return exactly {counts['unanswerable']} unanswerable questions.")
    if any(re.search(r"fictional|fictitious|made-up", x, re.I) for x in g.customers + g.unanswerable):
        errs.append("Never use the words 'fictional', 'fictitious' or 'made-up' in names or questions; just use the names.")
    return errs
