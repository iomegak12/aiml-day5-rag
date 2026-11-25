"""Prompt builders for every LLM call made by generate_corpus.py.

Each builder returns the *user* prompt; ``system(brief)`` is shared. Facts are passed
as compact JSON so the LLM writes prose around them without changing them.
"""

import json

from corpus_schemas import family


def _j(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False)


def system(brief: dict) -> str:
    v = brief["vendor"]
    return f"""You are a senior engineer and technical writer at {v['name']}, a fictional vendor of {v['domain']}.
You write for {v['team']}. Readers are {v['audience']}.

House style:
{brief['style']['guide'].strip()}

Return only the requested structured data."""


def _product_block(p: dict) -> str:
    fams: dict[str, list[str]] = {}
    for ver in p["versions"]:
        fams.setdefault(family(ver), []).append(ver)
    fam_txt = "; ".join(f"{f}: [{', '.join(vs)}]" for f, vs in fams.items())
    return f"""Product: {p['name']} ({p['kind']})
Releases, oldest to newest: {', '.join(p['versions'])}
Version families (major.minor) and their releases: {fam_txt}
CLI conventions: {p['cli']}
Typical problem areas: {p['focus']}"""


def _issue_view(it: dict) -> dict:
    keys = ["kb", "category", "code", "title", "symptoms", "root_cause", "workaround", "workaround_commands", "fix", "affected", "fixed_in"]
    return {k: it[k] for k in keys}


# ── Stage 1: facts ──────────────────────────────────────────────────────────
def product_issues(brief: dict, p: dict) -> str:
    c, t = brief["counts"], brief["traps"]
    n = c["issues_per_product"]
    one_fam = (" (here every family has exactly one release, so a defect lists exactly ONE affected release)"
               if all(len(v.split(".")) == 2 for v in p["versions"]) else "")
    return f"""Invent the knowledge-base issues for this product. They are the ground truth for a support knowledge base,
so they must be technically credible, specific and internally consistent.

{_product_block(p)}

Requirements
1. Exactly {n} distinct issues with refs I01 to I{n:02d}. Mix: software defects introduced in a specific release,
   configuration/design pitfalls, interoperability problems, performance problems and upgrade problems.
2. Versions. A software defect lists its affected releases, and ALL of them must come from ONE version family listed
   above{one_fam}. fixed_in is a strictly later release (it may be in a later family). A defect that affects the newest
   release {p['versions'][-1]} is still open: fixed_in=null. Configuration or design issues set affects_all_versions=true,
   affected_versions=[] and fixed_in=null. At least {c['min_fixed_issues_per_product']} issues must have a fixed_in release.
3. Version twins: exactly {t['version_twin_pairs_per_product']} pair. Two issues with very similar symptoms (for example the same
   protocol flapping) in DIFFERENT version families with DIFFERENT root causes, so only the version tells them apart.
   Set twin_of on both, pointing at each other. Each twin's engineer_question must mention one of its own affected versions.
4. Near-duplicates: exactly {t['near_duplicate_pairs_per_product']} pair. A second article about the same problem as an existing
   issue, with the SAME error_code but different title, symptoms and root-cause wording (as if written by another author).
   Set duplicate_of only on the second article and set its engineer_question to null. Near-duplicates are not twins.
5. Error codes. Most issues log a distinctive message (format in the house style). Use a different code for every
   issue, except that a near-duplicate pair shares its code. Never add suffixes such as -ALT or -2 to make codes differ.
6. engineer_question: how a customer or field engineer would really ask: informal, symptom-first, worded differently
   from the title, without the error code and without any KB number.
7. releases: exactly one entry per release with 1-3 features. A release that fixes defects may list a related improvement.
8. Use concrete values: timers, thresholds, counters, percentages, durations, exact command syntax."""


def guide_plan(brief: dict, p: dict, issues: list[dict]) -> str:
    c = brief["counts"]
    kbs = [{"kb": i["kb"], "title": i["title"], "workaround": i["workaround"], "commands": i["workaround_commands"]} for i in issues]
    return f"""Plan the "{p['name']} Configuration and Troubleshooting Guide", a PDF product guide.

{_product_block(p)}

Knowledge-base articles for this product (the guide's recommendations must be consistent with them):
{_j(kbs)}

Requirements
- title: the guide title.
- Exactly {c['guide_sections']} sections on recommended configuration and troubleshooting practice for this product.
  Each section has 2-4 key_facts (specific recommendations with concrete values) and 2-5 exact CLI commands.
  Where a KB workaround prescribes a setting, the matching section recommends the same values.
- related_kbs: KB IDs from the list above that a section helps prevent or diagnose (may be empty).
- Exactly {c['guide_questions_per_product']} how-to questions, each answered by the key_facts of a different section.
  Questions are phrased as an engineer would ask them (no KB numbers)."""


def global_facts(brief: dict) -> str:
    c = brief["counts"]
    prods = ", ".join(f"{p['name']} ({p['kind']})" for p in brief["products"])
    return f"""Generate supporting data for a fictional support knowledge base covering: {prods}.

1. customers: exactly {c['customers']} distinct fictional enterprise customer names across banking, healthcare, retail,
   logistics, education, energy, hospitality, telecom and public sector. Company names only, no real companies.
2. unanswerable: exactly {c['unanswerable']} realistic questions an engineer might ask that a technical knowledge base,
   release notes and configuration guides would NOT answer: list prices, licensing costs, roadmap or future releases,
   end-of-sale dates, integration with invented third-party products, comparisons with competitors' products.
   Mention the products above by name in most of them. Never write the words 'fictional' or 'fictitious':
   name invented products plainly, as a real engineer would."""


def near_duplicate(brief: dict, p: dict, original: dict) -> str:
    return f"""Write a second knowledge-base article about EXACTLY the same problem as the article below, as if another
TAC engineer had documented it independently: same product, affected releases, log message, root cause, workaround
and fix in substance, but a different title, different wording, different sentence structure and emphasis.
Keep every value identical (versions, timers, thresholds, counts, command names). Do not mention the other article.

{_product_block(p)}

Original article facts:
{_j(_issue_view(original))}"""


# ── Stage 2: documents ─────────────────────────────────────────────────────
def kb(brief: dict, p: dict, it: dict) -> str:
    extra = []
    if it["code"]:
        extra.append(f"- sample_output must contain the log message {it['code']} verbatim, with timestamps.")
    if it["fixed_in"]:
        extra.append(f"- resolution must state that the defect is fixed in release {it['fixed_in']}.")
    else:
        extra.append("- resolution explains that no software fix is required and how to prevent recurrence.")
    return f"""Write knowledge-base article {it['kb']} for this issue.

{_product_block(p)}

Facts (do not change any value):
{_j(_issue_view(it))}

Requirements
- 450-650 words in total across all fields; professional TAC knowledge-base tone.
- diagnosis_steps name the exact show/debug commands and what output indicates this issue.
- workaround_steps describe how to apply the workaround; the exact commands {it['workaround_commands']} are printed
  after your steps automatically, so refer to them but do not repeat them as a list.
{chr(10).join(extra)}
- Do not mention any document identifier (KB, release note, ticket or guide numbers)."""


def release_note(brief: dict, p: dict, version: str, prev: str | None, features: list[str],
                 fixed: list[dict], known: list[dict]) -> str:
    return f"""Write the release notes prose for {p['name']} release {version}.

{_product_block(p)}

Previous release in the train: {prev or 'none (first release covered)'}
New features, in this order (write one FeatureNote per feature, same order, same meaning):
{_j(features)}
Defects resolved in this release (listed automatically after your text): {_j([i['title'] for i in fixed]) if fixed else 'none'}
Known issues still present in this release (listed automatically): {_j([i['title'] for i in known]) if known else 'none'}

Requirements
- overview summarises the release (features and quality focus) in 80-140 words.
- compatibility covers supported upgrade sources, hardware, interoperability and configuration changes.
- upgrade_steps are concrete (backup, image verification, maintenance window, staged upgrade, post-checks).
- Do not mention any KB, ticket or document identifier and do not invent other releases."""


def tickets(brief: dict, p: dict, it: dict, specs: list[dict]) -> str:
    return f"""Write {len(specs)} resolved TAC support tickets for the same underlying issue, one per spec, in the same order.

{_product_block(p)}

Underlying issue (TAC knowledge-base article {it['kb']}):
{_j(_issue_view(it))}

Ticket specs:
{_j(specs)}

Requirements
- Each ticket reads like a real case from a different customer: the 'voice' says who opened it. Customers describe
  symptoms in their own words and sometimes with partial or misleading information. They do not know the KB number.
- description: the report plus initial TAC triage observations (3-6 sentences); mention the device and running version.
- If include_log_message is true, the description quotes the log message {it['code']} verbatim. If false, the log
  message must not appear anywhere in the ticket.
- resolution: what TAC did, citing {it['kb']}. If resolution_path is 'upgrade', the customer upgraded to {it['fixed_in']};
  otherwise TAC applied the workaround from {it['kb']}.
- Vary subjects, length and wording. No other document identifiers."""


def howto_tickets(brief: dict, p: dict, guide_id: str, specs: list[dict]) -> str:
    return f"""Write {len(specs)} resolved TAC support tickets that are how-to questions, one per spec, in the same order.

{_product_block(p)}

Ticket specs (each includes the question and the answer from the product guide):
{_j(specs)}

Requirements
- subject: a short how-to subject line. description: the customer's question in their own words with some context.
- resolution: TAC answered by pointing the customer to the product guide {guide_id} and summarising the relevant
  recommendation. It must contain the identifier {guide_id}. No other document identifiers."""


def guide_front(brief: dict, p: dict, guide: dict) -> str:
    return f"""Write the front matter for "{guide['title']}" ({guide['id']}).

{_product_block(p)}

Sections: {_j([s['heading'] for s in guide['sections']])}

Requirements: 'about' explains purpose and scope and how the guide complements knowledge-base articles and release notes;
'audience' states prerequisites; 'conventions' lists 3-5 typographic and command-syntax conventions."""


def guide_section(brief: dict, p: dict, guide: dict, sec: dict) -> str:
    return f"""Write section "{sec['heading']}" of "{guide['title']}".

{_product_block(p)}

The section's recommendations and commands are printed verbatim after your paragraphs:
Recommendations: {_j(sec['key_facts'])}
Commands: {_j(sec['commands'])}

Requirements
- paragraphs: 4-7 paragraphs (400-650 words total) explaining the design rationale, trade-offs, common mistakes and
  operational guidance. Restate the recommended values exactly where you mention them; never contradict them.
- procedure_steps: 3-7 ordered configuration steps.
- table: a useful parameter or reference table (3-6 rows), or null if none fits.
- verification: how to confirm the configuration works, naming show commands and expected output.
- No KB, ticket or document identifiers."""


def golden(kind: str, facts: dict, instruction: str) -> str:
    return f"""Write one evaluation question and its reference answer for a RAG benchmark over a support knowledge base.

Question type: {kind}
Instruction: {instruction}

Facts (the reference answer must use only these):
{_j(facts)}

The reference answer is 2-4 sentences, precise, and includes the concrete values from the facts."""
