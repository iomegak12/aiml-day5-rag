"""Generate the synthetic TAC knowledge corpus used by the RAG notebooks.

    uv run python scripts/generate_corpus.py            # writes ./data
    uv run python scripts/generate_corpus.py --out DIR  # custom location

Deterministic: same seed -> byte-identical output (PDFs included).
Everything is derived from scripts/facts.py, so ground truth is known.
"""

import argparse
import json
import random
import shutil
from datetime import date, timedelta
from pathlib import Path

from facts import CUSTOMERS, FEATURES, GUIDE_QUESTIONS, ISSUES, PRODUCTS, UNANSWERABLE

SEED = 42
ROOT = Path(__file__).resolve().parent.parent


# ── helpers ─────────────────────────────────────────────────────────────────
def family(versions) -> str:
    """'all' or the major.minor family, e.g. ['9.2.0','9.2.1'] -> '9.2'."""
    if versions == "all":
        return "all"
    fams = {".".join(v.split(".")[:2]) for v in versions}
    assert len(fams) == 1, versions
    return fams.pop()


def affected_str(issue) -> str:
    return "All versions" if issue["affected"] == "all" else ", ".join(issue["affected"])


def rn_id(p: str, v: str) -> str:
    return f"RN-{p}-{v}"


def front_matter(meta: dict) -> str:
    lines = ["---"] + [f"{k}: {json.dumps(v) if isinstance(v, str) else v}" for k, v in meta.items()] + ["---", ""]
    return "\n".join(lines)


# ── KB articles ─────────────────────────────────────────────────────────────
def write_kb(out: Path, rng: random.Random) -> list[dict]:
    d = out / "kb"
    d.mkdir(parents=True)
    docs = []
    for it in ISSUES:
        prod = PRODUCTS[it["p"]]
        updated = date(2026, 1, 1) + timedelta(days=rng.randint(0, 320))
        meta = {"doc_id": it["kb"], "doc_type": "kb", "product": prod["name"], "version_family": family(it["affected"]),
                "affected_versions": affected_str(it), "fixed_in": it["fixed_in"] or "n/a", "category": it["category"],
                "error_code": it["code"] or "none", "last_updated": updated.isoformat()}
        related = []
        if it["fixed_in"]:
            related.append(f"- Release notes: {rn_id(it['p'], it['fixed_in'])}")
        related.append(f"- Product guide: GUIDE-{it['p']}")
        body = f"""# {it['kb']}: {it['title']}

## Symptoms
{it['symptoms']}

## Environment
- Product: {prod['name']} ({prod['kind']})
- Affected versions: {affected_str(it)}
- Fixed in: {it['fixed_in'] or 'not applicable'}
- Log message: {it['code'] or 'none'}

## Root cause
{it['root_cause']}

## Workaround
{it['workaround']}

## Resolution
{it['fix']}

## Related
{chr(10).join(related)}
"""
        (d / f"{it['kb']}.md").write_text(front_matter(meta) + body, encoding="utf-8")
        docs.append(meta)
    return docs


# ── Release notes ───────────────────────────────────────────────────────────
def write_release_notes(out: Path) -> list[dict]:
    d = out / "release_notes"
    d.mkdir(parents=True)
    docs = []
    for p, prod in PRODUCTS.items():
        for i, v in enumerate(prod["versions"]):
            fixed = [it for it in ISSUES if it["p"] == p and it["fixed_in"] == v]
            known = [it for it in ISSUES if it["p"] == p and it["affected"] != "all" and v in it["affected"]]
            rid = rn_id(p, v)
            meta = {"doc_id": rid, "doc_type": "release_note", "product": prod["name"], "version": v,
                    "version_family": ".".join(v.split(".")[:2])}
            prev = prod["versions"][i - 1] if i else None
            fixed_md = "\n".join(f"- {it['kb']}: {it['title']} ({it['code'] or 'no log message'})" for it in fixed) or "- None"
            known_md = "\n".join(f"- {it['kb']}: {it['title']}. Workaround: {it['workaround']}" for it in known) or "- None"
            feats = "\n".join(f"- {f}" for f in FEATURES[p][v])
            body = f"""# {prod['name']} release {v}: release notes

## New features
{feats}

## Resolved issues
{fixed_md}

## Known issues
{known_md}

## Upgrade notes
{f'Supported direct upgrade path from {prev}.' if prev else 'Initial release in this train.'} Back up the configuration before upgrading and review the known issues above.
"""
            (d / f"{rid}.md").write_text(front_matter(meta) + body, encoding="utf-8")
            docs.append(meta)
    return docs


# ── Resolved tickets ────────────────────────────────────────────────────────
OPENERS = ["Customer reports that", "Engineer on site says", "NOC escalation:", "Raised by the customer's network team:", "Customer called in:"]
SEVERITY = ["P1", "P2", "P2", "P3", "P3", "P3", "P4"]


def lower_first(s: str) -> str:
    return s[0].lower() + s[1:]


def write_tickets(out: Path, rng: random.Random) -> list[dict]:
    d = out / "tickets"
    d.mkdir(parents=True)
    tickets, n = [], 50001
    primaries = [it for it in ISSUES if it["q"] is not None]          # near-duplicate KBs are not referenced
    for it in primaries:
        prod = PRODUCTS[it["p"]]
        versions = prod["versions"] if it["affected"] == "all" else it["affected"]
        for _ in range(5):
            v = rng.choice(versions)
            opened = date(2026, 1, 5) + timedelta(days=rng.randint(0, 310))
            first_sentence = it["symptoms"].split(". ")[0].rstrip(".") + "."
            desc = f"{rng.choice(OPENERS)} {lower_first(first_sentence)} Device: {prod['name']} running {v}."
            if it["code"] and rng.random() < 0.6:
                desc += f" Log shows {it['code']}."
            if it["fixed_in"] and rng.random() < 0.4:
                resolution = f"Upgraded to {it['fixed_in']} per {it['kb']}. Issue resolved."
            else:
                resolution = f"Applied workaround from {it['kb']}: {it['workaround']}"
            tickets.append({"ticket_id": f"TKT-{n}", "doc_type": "ticket", "customer": rng.choice(CUSTOMERS),
                            "product": prod["name"], "version": v, "severity": rng.choice(SEVERITY),
                            "opened": opened.isoformat(), "closed": (opened + timedelta(days=rng.randint(1, 14))).isoformat(),
                            "subject": it["title"].split(" due to ")[0].split(" caused by ")[0].split(" because ")[0],
                            "description": desc, "resolution": resolution, "kb_refs": [it["kb"]],
                            "error_code": it["code"] or ""})
            n += 1
    for g in GUIDE_QUESTIONS + GUIDE_QUESTIONS[:2] + GUIDE_QUESTIONS[:2]:       # 8 how-to tickets resolved from guides
        prod = PRODUCTS[g["p"]]
        opened = date(2026, 1, 5) + timedelta(days=rng.randint(0, 310))
        tickets.append({"ticket_id": f"TKT-{n}", "doc_type": "ticket", "customer": rng.choice(CUSTOMERS),
                        "product": prod["name"], "version": rng.choice(prod["versions"]), "severity": "P4",
                        "opened": opened.isoformat(), "closed": (opened + timedelta(days=rng.randint(1, 5))).isoformat(),
                        "subject": "How-to question", "description": f"Customer asks: {g['q']}",
                        "resolution": f"Pointed customer to GUIDE-{g['p']}.", "kb_refs": [], "error_code": ""})
        n += 1
    rng.shuffle(tickets)
    (d / "resolved_tickets.json").write_text(json.dumps(tickets, indent=2), encoding="utf-8")
    return tickets


# ── Product guides (PDF) ────────────────────────────────────────────────────
GUIDE_SECTIONS = {
    "AR": [("Routing: BGP and BFD", [
        "For BGP sessions to service providers, Aurora recommends BFD with an interval of 300 ms, a minimum receive interval of 300 ms and a multiplier of 3. Shorter timers detect failures faster but make sessions sensitive to control-plane load.",
        "Configure timers explicitly on every neighbor instead of relying on release defaults, because defaults can change between releases."],
        ["bfd interval 300 min-rx 300 multiplier 3", "neighbor 198.51.100.23 fall-over bfd"]),
        ("Protecting the control plane", [
        "Management traffic such as SNMP and SSH is processed by the control plane. Apply control-plane policing so that bursts of management traffic cannot starve routing protocols.",
        "Limit SNMP to the MIB subtrees your monitoring system needs. Exclude the routing tables from SNMP views on routers that carry full Internet routes."],
        ["snmp-server view NMS iso included", "snmp-server view NMS ipRouteTable excluded", "control-plane service-policy input COPP"])],
    "NF": [("Site-to-site IPsec VPN", [
        "Use IKEv2 for all new site-to-site tunnels. Configure the IKE SA lifetime explicitly, and give the two peers different lifetimes or enable rekey jitter so that both sides never start a rekey at the same moment.",
        "Dead peer detection settings must match on both peers. Use an interval of 10 seconds and 3 retries unless a provider requires otherwise."],
        ["crypto ikev2 sa-lifetime 86400", "crypto ikev2 rekey-jitter 10", "crypto ikev2 dpd 10 3"]),
        ("High availability", [
        "Carry HA heartbeats on a dedicated link. If a dedicated link is not possible, configure a second heartbeat path over a separate VLAN.",
        "After an interrupted firmware update, recover the previous image from the console."],
        ["ha heartbeat interface ha1 priority 1", "ha heartbeat interface ha2 priority 2", "system recover"])],
    "OW": [("Controller redundancy (N+1)", [
        "In an N+1 design, one standby controller backs up several primary controllers. Configure each access point with a primary and a secondary controller, and enable fast failover so that access points move to the standby within seconds.",
        "Pre-associate access points with the standby controller so that they do not need to discover it during an outage."],
        ["redundancy mode n-plus-1", "ap primary-controller WLC-A", "ap secondary-controller WLC-STANDBY", "ap fast-failover"]),
        ("Roaming and guest access", [
        "Enable 802.11r consistently on every WLAN that shares an SSID. Mixed settings cause roaming failures for voice and scanner clients.",
        "Guest portals cannot redirect HTTPS traffic without certificate warnings. Enable captive-portal detection so that client devices open the portal automatically."],
        ["wlan corp ft enable", "guest-portal captive-detection enable"])],
    "AT": [("Application-aware routing", [
        "Define SLA classes for latency-sensitive applications. For voice, a typical class requires jitter below 30 ms and loss below 1 percent.",
        "Match voice traffic on DSCP EF, prefer the MPLS transport, and allow failover to broadband only when the SLA class is violated."],
        ["sla-class VOICE jitter 30 loss 1", "app-route-policy VOICE match dscp ef prefer mpls"]),
        ("Transport and certificates", [
        "LTE carriers often use a smaller MTU. Set the tunnel MTU to 1400 on LTE interfaces and enable TCP MSS clamping.",
        "Edge certificates are shown under Devices, Certificates. Releases before 3.1 require manual renewal before expiry."],
        ["interface lte0 tunnel-mtu 1400", "tcp-mss-adjust 1360"])],
    "HX": [("Optics and transceiver diagnostics", [
        "Use the transceiver diagnostics command to check receive and transmit power, temperature and voltage for every optic. Compare receive power with the low-warning and low-alarm thresholds.",
        "If receive power is low, clean both connectors before replacing the optic."],
        ["show interfaces transceiver detail", "show interfaces ethernet1/49 transceiver"]),
        ("Stacking and switching", [
        "Set explicit stack member priorities so that stack election is deterministic, and upgrade members one at a time.",
        "Keep spanning tree enabled on all access switches. MAC flap messages identify the ports involved in a loop."],
        ["stack member 1 priority 15", "spanning-tree mode rapid-pvst", "show mac address-table flapping"])],
}


def write_guides(out: Path) -> list[dict]:
    from reportlab import rl_config
    rl_config.invariant = 1                                   # deterministic PDF bytes
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

    d = out / "guides"
    d.mkdir(parents=True)
    ss = getSampleStyleSheet()
    docs = []
    for p, prod in PRODUCTS.items():
        gid = f"GUIDE-{p}"
        issues = [it for it in ISSUES if it["p"] == p]
        story = [Paragraph(f"{prod['name']} Configuration and Troubleshooting Guide", ss["Title"]),
                 Paragraph(f"Document {gid}. Applies to releases {', '.join(prod['versions'])}.", ss["Normal"]), Spacer(1, 12),
                 Paragraph("About this guide", ss["Heading1"]),
                 Paragraph(f"This guide describes recommended configuration and troubleshooting practices for the {prod['name']} {prod['kind']}. "
                           "It complements the knowledge base and the release notes, which describe specific issues and fixes.", ss["Normal"]),
                 PageBreak()]
        for heading, paras, cmds in GUIDE_SECTIONS[p]:
            story += [Paragraph(heading, ss["Heading1"])] + [Paragraph(t, ss["Normal"]) for t in paras]
            story += [Spacer(1, 8), Preformatted("\n".join(cmds), ss["Code"]), PageBreak()]
        story += [Paragraph("Software upgrades", ss["Heading1"]),
                  Paragraph(f"Supported releases: {', '.join(prod['versions'])}. Always read the release notes for the target release, "
                            "back up the configuration, and upgrade during a maintenance window.", ss["Normal"]), PageBreak(),
                  Paragraph("Log message reference", ss["Heading1"])]
        for it in issues:
            if it["code"]:
                story.append(Paragraph(f"<b>{it['code']}</b>: {it['title']}. See {it['kb']}.", ss["Normal"]))
        doc = SimpleDocTemplate(str(d / f"{gid}.pdf"), pagesize=A4, title=f"{prod['name']} Guide", author="TAC Documentation")
        doc.build(story, onFirstPage=lambda c, _d: None,
                  onLaterPages=lambda c, _d: c.drawString(500, 20, f"Page {c.getPageNumber()}"))
        docs.append({"doc_id": gid, "doc_type": "guide", "product": prod["name"]})
    return docs


# ── Golden evaluation set ───────────────────────────────────────────────────
def write_golden(out: Path, rng: random.Random, tickets: list[dict]) -> list[dict]:
    d = out / "eval"
    d.mkdir(parents=True)
    by_kb = {it["kb"]: it for it in ISSUES}
    name = lambda it: PRODUCTS[it["p"]]["name"]
    answer = lambda it: f"{it['root_cause']} Workaround: {it['workaround']} {it['fix']}"
    items = []

    def add(qtype, question, expected, ref, filters=None):
        items.append({"id": f"Q{len(items) + 1:02d}", "type": qtype, "question": question,
                      "expected_doc_ids": expected, "reference_answer": ref, "filters": filters or {}})

    twins = [it for it in ISSUES if "version_twin" in it["traps"]]
    singles = [it for it in ISSUES if it["q"] and "version_twin" not in it["traps"]]
    rng.shuffle(singles)
    for it in sorted(singles[:14], key=lambda x: x["kb"]):
        exp = [it["kb"]] + [o["kb"] for o in ISSUES if o is not it and o["code"] and o["code"] == it["code"]]
        add("single_hop", it["q"], exp, answer(it))
    for it in twins:
        v = it["affected"][-1]
        add("version_specific", it["q"], [it["kb"]], answer(it), {"product": name(it), "version": v})
    for code in ["%IKE-3-REKEY_COLLISION", "ERR-ORCH-4412", "%STACK-2-SPLIT_DETECTED", "%WLC-2-AP_JOIN_TIMEOUT", "%FW-2-SESSION_LIMIT", "%SYS-4-CPU_HIGH"]:
        hits = [it for it in ISSUES if it["code"] == code]
        # Any document that literally contains the code is valid evidence: the KB article(s),
        # resolved tickets that logged it, and release notes that list it as fixed.
        evidence = [h["kb"] for h in hits]
        evidence += sorted(t["ticket_id"] for t in tickets if t["error_code"] == code)
        evidence += [rn_id(h["p"], h["fixed_in"]) for h in hits if h["fixed_in"]]
        add("error_code", f"What does {code} mean, and what should we do about it?", evidence, answer(hits[0]))
    for kb in ["KB-2101", "KB-3101", "KB-4101", "KB-5103", "KB-6104", "KB-3106"]:
        it = by_kb[kb]
        v = it["affected"][-1]
        add("multi_hop", f"A customer on {name(it)} {v} is affected by {it['kb']}. Which release fixes it, and what should they do until they can upgrade?",
            [it["kb"], rn_id(it["p"], it["fixed_in"])], f"Fixed in {it['fixed_in']} ({rn_id(it['p'], it['fixed_in'])}). Until then: {it['workaround']}",
            {"product": name(it), "version": v})
    for g in GUIDE_QUESTIONS:
        sec = GUIDE_SECTIONS[g["p"]][0]
        add("how_to", g["q"], [f"GUIDE-{g['p']}"] + g["also"], " ".join(sec[1]) + " Commands: " + "; ".join(sec[2]))
    for kb in ["KB-3101", "KB-6104"]:
        it = by_kb[kb]
        tids = sorted(t["ticket_id"] for t in tickets if kb in t["kb_refs"])
        add("similar_case", f"Have other customers reported this before: {lower_first(it['symptoms'].split('. ')[0])}? How was it resolved?",
            tids + [kb], answer(it))
    for q in UNANSWERABLE:
        add("unanswerable", q, [], "The knowledge base does not contain this information.")
    (d / "golden_set.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    return items


# ── main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "data"), help="output directory (default: ./data)")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    rng = random.Random(args.seed)

    kb = write_kb(out, rng)
    rn = write_release_notes(out)
    tk = write_tickets(out, rng)
    gd = write_guides(out)
    gs = write_golden(out, rng, tk)
    manifest = {"seed": args.seed, "counts": {"kb": len(kb), "release_notes": len(rn), "tickets": len(tk), "guides": len(gd), "golden_questions": len(gs)},
                "golden_types": {t: sum(1 for g in gs if g["type"] == t) for t in dict.fromkeys(g["type"] for g in gs)}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Corpus written to {out}")
    for k, v in manifest["counts"].items():
        print(f"  {k:17s} {v}")
    print("  golden types     ", manifest["golden_types"])


if __name__ == "__main__":
    main()
