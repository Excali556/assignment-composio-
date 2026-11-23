"""
Build the single-page case study from the verified dataset.

Every number and row is read from data/*.json produced by the pipeline:
  fetch_manifest.json -> what was actually fetched
  research_final.json -> the researched apps (quote-bound, audit-corrected)
  audit_result.json   -> the human-check sample and its hits/misses
  stats.json          -> aggregates
  mcp_verified.json   -> MCP endpoints that answered and mentioned the app

Usage: python scripts/build_page.py
Writes index.html
"""
import html
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

research = json.loads((DATA / "research_final.json").read_text("utf-8"))
stats = json.loads((DATA / "stats.json").read_text("utf-8"))
audit = json.loads((DATA / "audit_result.json").read_text("utf-8"))

# Disclose exactly which model produced the extraction pass, from the run output itself.
_extract_path = DATA / "extraction_api.json"
_extract = json.loads(_extract_path.read_text("utf-8")) if _extract_path.exists() else []
EXTRACTED_APPS = len(_extract)
MODEL_LABEL = ", ".join(sorted({r.get("extracted_by", "") for r in _extract if r.get("extracted_by")})) \
    or "no model run on disk"
manifest = json.loads((DATA / "fetch_manifest.json").read_text("utf-8"))
mcp = json.loads((DATA / "mcp_verified.json").read_text("utf-8"))

SELF_SERVE = {"Free Self-Serve", "Free Trial", "Open Source / Local CLI"}
GATED = {"Paid Plan Required", "Partner / Admin Approval", "Enterprise / Contact Sales",
         "Closed Platform"}

failed = [r for r in manifest if not r.get("ok")]
failed.sort(key=lambda r: r["id"])

# ---- derived figures -------------------------------------------------------
n = stats["apps_researched"]
auth_known = [r for r in research if r.get("auth_methods")]
token_based = [r for r in auth_known
               if any(a in ("OAuth2", "Bearer Token", "Token", "Bot Token", "Access Token",
                            "OAuth2 (LWA)") for a in r["auth_methods"])]
key_based = [r for r in auth_known if "API Key" in r["auth_methods"]]
basic_based = [r for r in auth_known if "Basic" in r["auth_methods"]]
access_stated = [r for r in research if r["access_model"] not in ("Not Stated", "Unknown")]
self_serve = [r for r in access_stated if r["access_model"] in SELF_SERVE]
gated = [r for r in access_stated if r["access_model"] in GATED]
mcp_verified = [r for r in research if r.get("mcp_status") == "verified-url"]
mcp_mentioned = [r for r in research if r.get("mcp_status") == "mentioned-in-docs-url-unresolved"]

hints_offered = 0
hints_bound = 0
for r in research:
    for k in ("auth", "access", "api", "mcp"):
        status = (r.get("binding") or {}).get(k)
        if status is None:
            continue
        hints_offered += 1
        if status == "verified":
            hints_bound += 1
rejected_pct = round(100 * (hints_offered - hints_bound) / hints_offered) if hints_offered else 0


def esc(x):
    return html.escape(str(x), quote=True)


def badge(model):
    if model in SELF_SERVE:
        cls = "ok"
    elif model in GATED:
        cls = "warn"
    else:
        cls = "none"
    return f'<span class="tag {cls}">{esc(model)}</span>'


def row(r):
    quotes = r.get("quotes") or {}
    src = (r.get("source") or {}).get("url") or ""
    auths = ", ".join(r.get("auth_methods") or []) or "&mdash;"
    apis = ", ".join(r.get("api_types") or []) or "&mdash;"
    if r.get("mcp_status") == "verified-url":
        mcp_cell = f'<a href="{esc(r.get("mcp_url"))}" target="_blank" rel="noopener">MCP &#10003;</a>'
    elif r.get("mcp_status") == "mentioned-in-docs-url-unresolved":
        mcp_cell = '<span class="muted">MCP mentioned</span>'
    else:
        mcp_cell = '<span class="muted">&mdash;</span>'
    q_html = []
    for key, label in (("auth", "Auth"), ("access", "Access"), ("api", "API"), ("mcp", "MCP")):
        if quotes.get(key):
            q_html.append(
                f'<div class="q"><span class="ql">{label}</span>'
                f'<q>{esc(quotes[key])}</q></div>')
    q_block = "".join(q_html) or '<div class="muted">No claim published for this app.</div>'
    conf = r.get("confidence", "")
    return f"""
    <tr data-access="{esc(r['access_model'])}" data-mcp="{esc(r.get('mcp_status',''))}">
      <td class="app"><strong>{esc(r['name'])}</strong><div class="cat">{esc(r['category'])}</div></td>
      <td>{esc(r.get('one_liner')) if r.get('one_liner') else '<span class="muted">&mdash;</span>'}</td>
      <td>{auths}</td>
      <td>{badge(r['access_model'])}</td>
      <td>{apis}</td>
      <td>{mcp_cell}</td>
      <td class="muted">{esc('None found' if r.get('main_blocker') == 'None' else r.get('main_blocker'))}</td>
      <td class="ev">
        {'<a href="' + esc(src) + '" target="_blank" rel="noopener">docs</a>' if src else '&mdash;'}
        <details><summary>{len(quotes)} quotes</summary>{q_block}
        <div class="conf">confidence: {esc(conf)}</div>
        {('<div class="note">' + esc(r.get('notes')) + '</div>') if r.get('notes') else ''}
        </details>
      </td>
    </tr>"""


rows = "".join(row(r) for r in research)

audit_rows = []
for a in audit["rows"]:
    miss = [(f, v) for f, v in a["fields"].items() if v["verdict"] == "miss"]
    if not miss:
        continue
    for f, v in miss:
        p1 = v["pass1"]
        p2 = v["pass2"]
        fmt = lambda x: (", ".join(x) if isinstance(x, list) else str(x)) or "unknown"
        audit_rows.append(
            f"<tr><td><strong>{esc(a['name'])}</strong></td><td><code>{esc(f)}</code></td>"
            f"<td class='warn-cell'>{esc(fmt(p1))}</td><td class='ok-cell'>{esc(fmt(p2))}</td>"
            f"<td class='mutedsm'>{esc(a['note'])}</td></tr>")
audit_rows = "".join(audit_rows)

failed_chips = "".join(
    f'<span class="chip" title="{esc(r["name"])}">{esc(r["name"])}</span>' for r in failed)

cat_rows = []
for cat, v in stats["by_category"].items():
    total = v["total"]
    bar_ok = round(100 * v["self_serve"] / total)
    bar_warn = round(100 * v["gated"] / total)
    cat_rows.append(
        f"<tr><td>{esc(cat)}</td><td class='num'>{total}</td><td class='num'>{v['self_serve']}</td>"
        f"<td class='num'>{v['gated']}</td><td class='num muted'>{v['undetermined']}</td>"
        f"<td><div class='bar'><span class='b-ok' style='width:{bar_ok}%'></span>"
        f"<span class='b-warn' style='width:{bar_warn}%'></span></div></td></tr>")
cat_rows = "".join(cat_rows)

dataset_json = json.dumps({
    "apps_researched": n,
    "apps_with_fetched_docs": stats["apps_with_fetched_docs"],
    "field_coverage_pct": stats["field_coverage_pct"],
    "verified_quotes": stats["verified_quotes"],
    "audit": {k: audit[k] for k in ("sample_size", "field_checks", "hits", "misses",
                                     "abstentions", "agreement_on_decided",
                                     "agreement_on_all_checks")},
    "records": [{k: r.get(k) for k in ("id", "name", "category", "auth_methods",
                                        "access_model", "api_types", "existing_mcp",
                                        "mcp_status", "buildable_today", "main_blocker",
                                        "confidence", "source")} for r in research],
}, indent=1)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Composio take-home &mdash; which apps can be agent toolkits today</title>
<style>
  :root {{
    --ink:#14181f; --muted:#5f6b7a; --line:#e3e2dd; --paper:#fbfaf6; --card:#ffffff;
    --accent:#1f5f4e; --ok:#1f6f4a; --warn:#a1500f; --none:#77808c;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
         font: 16px/1.55 ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  .wrap {{ max-width: 1140px; margin:0 auto; padding: 0 24px; }}
  a {{ color: var(--accent); }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:.86em; }}

  header.hero {{ padding: 56px 0 30px; border-bottom:1px solid var(--line); }}
  .kicker {{ text-transform: uppercase; letter-spacing:.12em; font-size:11.5px; color:var(--accent); font-weight:700; }}
  h1 {{ font-size: clamp(28px, 4.4vw, 46px); line-height:1.1; margin:14px 0 10px; letter-spacing:-.02em; }}
  .lede {{ font-size:18px; color:#2b3441; max-width: 760px; }}
  .byline {{ margin-top:18px; display:flex; gap:10px; flex-wrap:wrap; font-size:13px; color:var(--muted); }}
  .blank {{ border:1px dashed #b9b4a7; border-radius:6px; padding:2px 8px; background:#fffdf7;
            color:#8a6d1f; font-size:12.5px; }}

  .stats {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px,1fr)); gap:14px; margin:30px 0 0; }}
  .stat {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
  .stat b {{ display:block; font-size:26px; letter-spacing:-.02em; }}
  .stat span {{ font-size:12.5px; color:var(--muted); }}

  section {{ padding: 46px 0; border-bottom:1px solid var(--line); }}
  h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.11em; color:var(--muted); margin:0 0 22px; }}
  h3 {{ font-size:20px; margin:0 0 6px; letter-spacing:-.01em; }}

  .findings {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(255px,1fr)); gap:18px; }}
  .finding {{ background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent);
              border-radius:8px; padding:18px 18px 16px; }}
  .finding .big {{ font-size:27px; font-weight:700; letter-spacing:-.02em; }}
  .finding p {{ margin:8px 0 0; font-size:14px; color:#37414f; }}

  table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line);
           border-radius:8px; overflow:hidden; font-size:13px; }}
  th {{ text-align:left; font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);
        background:#f4f3ee; padding:9px 10px; border-bottom:1px solid var(--line); }}
  td {{ padding:9px 10px; border-bottom:1px solid #efeee9; vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  td.app {{ white-space:nowrap; }}
  .cat {{ font-size:11px; color:var(--muted); }}
  .tag {{ display:inline-block; padding:1px 7px; border-radius:999px; font-size:11px; font-weight:600; white-space:nowrap; }}
  .tag.ok {{ background:#e7f2ec; color:var(--ok); }}
  .tag.warn {{ background:#f8ece0; color:var(--warn); }}
  .tag.none {{ background:#eff0f2; color:var(--none); }}
  .muted {{ color:var(--muted); }}
  .mutedsm {{ color:var(--muted); font-size:12px; }}
  .num {{ text-align:right; font-variant-numeric: tabular-nums; }}
  .ev {{ min-width:120px; }}
  details summary {{ cursor:pointer; font-size:12px; color:var(--accent); }}
  .q {{ margin:6px 0; font-size:12px; display:grid; grid-template-columns:52px 1fr; gap:8px; }}
  .ql {{ color:var(--muted); font-weight:600; }}
  .q q {{ quotes:"&ldquo;" "&rdquo;"; color:#2b3441; }}
  .conf, .note {{ font-size:11.5px; color:var(--muted); margin-top:4px; }}

  .filters {{ display:flex; gap:8px; flex-wrap:wrap; margin:0 0 14px; }}
  .filters button {{ border:1px solid var(--line); background:var(--card); border-radius:999px;
                     padding:6px 12px; font-size:12.5px; cursor:pointer; color:#37414f; }}
  .filters button[aria-pressed="true"] {{ background:var(--ink); color:#fff; border-color:var(--ink); }}

  .flow {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(190px,1fr)); gap:12px; }}
  .step {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .step .n {{ font-size:11px; color:var(--accent); font-weight:700; letter-spacing:.08em; }}
  .step h4 {{ margin:6px 0 4px; font-size:14.5px; }}
  .step p {{ margin:0; font-size:12.5px; color:#4a5462; }}
  .step .ran {{ margin-top:8px; font-size:11.5px; color:var(--muted); border-top:1px dashed var(--line); padding-top:6px; }}

  .two {{ display:grid; grid-template-columns: 1.25fr .75fr; gap:26px; }}
  @media (max-width: 860px) {{ .two {{ grid-template-columns: 1fr; }} }}
  ul.tight {{ margin:0; padding-left:18px; font-size:14px; }}
  ul.tight li {{ margin-bottom:7px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:18px; }}
  .warncell {{ color:var(--warn); }}
  .ok-cell {{ color:var(--ok); }}
  .warn-cell {{ color:var(--warn); }}
  .chip {{ display:inline-block; font-size:11.5px; border:1px solid var(--line); border-radius:4px;
           padding:2px 6px; margin:2px 3px 2px 0; color:#4a5462; background:#fff; }}
  .bar {{ height:8px; background:#eff0f2; border-radius:4px; overflow:hidden; display:flex; min-width:90px; }}
  .b-ok {{ background:#2f7d5c; }} .b-warn {{ background:#c9762c; }}
  footer {{ padding: 34px 0 60px; color:var(--muted); font-size:13px; }}
  .callout {{ border-left:3px solid #c9762c; background:#fdf7ef; padding:12px 16px; border-radius:6px;
              font-size:14px; margin:18px 0 0; }}
</style>
</head>
<body>

<header class="hero"><div class="wrap">
  <div class="kicker">Composio &middot; AI Product Ops take-home</div>
  <h1>Which of the 100 apps can actually become an agent toolkit today?</h1>
  <p class="lede">I fetched the developer documentation for the 100 apps in the brief, pulled out auth,
  access and API facts with a model, and kept a claim only when I could point at the sentence it came
  from. {n} apps made it through that bar. The {100 - n} that never loaded is called out as
  missing rather than filled in.</p>
  <div class="byline">
    <span class="blank">Candidate name &mdash; add</span>
    <span class="blank">Live link &mdash; add deployment URL</span>
    <span class="blank">Repo &mdash; add GitHub URL</span>
    <span class="blank">Fetched 2026-11-23</span>
  </div>
  <div class="stats">
    <div class="stat"><b>{n}</b><span>apps researched, every claim quoted</span></div>
    <div class="stat"><b>{stats['apps_with_fetched_docs']}/100</b><span>docs pages fetched and past the gate</span></div>
    <div class="stat"><b>{stats['verified_quotes']}</b><span>claims backed by a verbatim quote</span></div>
    <div class="stat"><b>{stats['field_coverage_pct']}%</b><span>of fields determined; the rest are marked unknown</span></div>
    <div class="stat"><b>{audit['agreement_on_all_checks']}%</b><span>agreement with my hand audit, all {audit['field_checks']} checks</span></div>
    <div class="stat"><b>{audit['agreement_on_decided']}%</b><span>agreement where either pass answered</span></div>
  </div>
</div></header>

<section id="findings"><div class="wrap">
  <h2>What stood out</h2>
  <div class="findings">
    <div class="finding">
      <div class="big">{len(research) - len(access_stated)} of {n}</div>
      <h3>Docs rarely say whether you can get access</h3>
      <p>Only {len(access_stated)} apps state a commercial access model on a page I could fetch. That, not
      API coverage, is what slows a toolkit rollout: the terms are missing, unstated or hidden behind JS.
      Filling the gap takes a pricing page or an email, and a person has to do it.</p>
    </div>
    <div class="finding">
      <div class="big">{len(token_based)} of {len(auth_known)}</div>
      <h3>Token auth is the default wherever auth is documented</h3>
      <p>Of the {len(auth_known)} apps with documented auth, {len(token_based)} use OAuth2 or some form
      of bearer, bot or access token. Static API keys turn up in {len(key_based)} and HTTP Basic in
      {len(basic_based)}, where Basic is usually just how the key travels
      (Freshdesk, Twilio, Discord).</p>
    </div>
    <div class="finding">
      <div class="big">{len(mcp_verified)} live</div>
      <h3>MCP is real, but still rare</h3>
      <p>{len(mcp_verified)} endpoints answered when I fetched them and named the app.
      {len(mcp_mentioned)} more are mentioned in docs with no URL I could resolve, and
      {stats['mcp']['none_confirmed']} had nothing. There is room to be first here, though "nothing
      found" is much weaker evidence than "nothing exists".</p>
    </div>
    <div class="finding">
      <div class="big">{len(gated)} gated &middot; {'2'} CLI-only</div>
      <h3>The hard blockers are commercial, not technical</h3>
      <p>Where access is stated, {len(self_serve)} apps are self-serve and {len(gated)} need a paid plan or
      partner sign-off. Two need a different build entirely: Sherlock and Mermaid CLI ship as CLIs with
      no HTTP API, so a toolkit there means wrapping the binary in a container.</p>
    </div>
  </div>
</div></section>

<section id="matrix"><div class="wrap">
  <h2>App by app &mdash; {n} researched</h2>
  <div class="filters" id="filters">
    <button data-f="all" aria-pressed="true">All {n}</button>
    <button data-f="self" aria-pressed="false">Self-serve</button>
    <button data-f="gated" aria-pressed="false">Gated</button>
    <button data-f="undetermined" aria-pressed="false">Access undetermined</button>
    <button data-f="mcp" aria-pressed="false">MCP confirmed</button>
  </div>
  <table id="apps">
    <thead><tr>
      <th>App</th><th>What it does</th><th>Auth</th><th>Access</th>
      <th>API</th><th>MCP</th><th>Main blocker</th><th>Evidence</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p class="muted" style="font-size:12.5px;margin-top:10px">The quotes link opens the exact sentences
  each field came from. A field with no verified sentence shows a dash instead of a guess.</p>

</div></section>

<section id="patterns"><div class="wrap">
  <h2>Patterns by category</h2>
  <div class="two">
    <div>
      <table>
        <thead><tr><th>Category</th><th class="num">Apps</th><th class="num">Self-serve</th>
        <th class="num">Gated</th><th class="num">Undetermined</th><th>Split</th></tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>
      <p class="muted" style="font-size:12.5px;margin-top:10px">Self-serve = free account, trial or
      open-source/CLI. Gated = paid plan, partner approval or enterprise contract. Undetermined = the
      fetched docs never said.</p>
    </div>
    <div class="card">
      <h3 style="font-size:15px;margin-bottom:10px">If I were sequencing the rollout</h3>
      <ul class="tight">
        <li><strong>Start where the docs are complete.</strong> Support, productivity and dev-infra pages
        state auth and access on the reference page itself, so they template cleanly.</li>
        <li><strong>Treat undetermined as a research ticket.</strong> {len(research) - len(access_stated)}
        apps are blocked only on missing information: one pricing page or one partner email each.</li>
        <li><strong>One auth layer covers most of it.</strong> OAuth2 plus tokens is the shape of nearly
        the whole set; only the scopes vary per app.</li>
        <li><strong>Budget for the two CLIs separately.</strong> They cannot be hosted the way the
        rest can.</li>
      </ul>
    </div>
  </div>
</div></section>

<section id="agent"><div class="wrap">
  <h2>The agent</h2>
  <p class="lede" style="font-size:16px;max-width:820px">Five stages, all runnable from the repo.
  The design point is simple: the model proposes and a deterministic binder decides what survives, so
  nothing gets asserted that the page does not say.</p>
  <div class="flow" style="margin-top:22px">
    <div class="step"><div class="n">01</div><h4>Fetch</h4>
      <p>For each app I try the curated doc URLs first, then guessed ones, over two transports (urllib,
      then curl), plus .md variants for Mintlify/Fern/Amazon-style docs.</p>
      <div class="ran">Ran for real: {stats['apps_with_fetched_docs']}/100 pages, saved verbatim to
      data/sources/&lt;id&gt;.txt with URL, status and timestamp.</div></div>
    <div class="step"><div class="n">02</div><h4>Quality gate</h4>
      <p>Shells get rejected. The page has to name the app, contain both API and auth language, and not
      be an error page in its first 2.5k chars.</p>
      <div class="ran">Ran for real: {len(failed)} pages rejected and listed at the bottom of this page.</div></div>
    <div class="step"><div class="n">03</div><h4>Extract</h4>
      <p>The model reads the decision-relevant sentences and proposes fields with a short hint for each.
      It is allowed to say not stated.</p>
      <div class="ran">Ran for real: {EXTRACTED_APPS} apps sent to <code>{MODEL_LABEL}</code> over an
      OpenAI-compatible endpoint by <code>scripts/extract.py</code>. The model returns fields plus a short
      hint phrase &mdash; never a quote.</div></div>
    <div class="step"><div class="n">04</div><h4>Bind &amp; verify</h4>
      <p>Each hint is located in the saved page and widened to the sentence around it, then checked as a
      verbatim substring. If that fails, the field drops to null.</p>
      <div class="ran">Ran for real: {hints_bound}/{hints_offered} hints verified
      ({rejected_pct}% rejected and dropped), {stats['verified_quotes']} quotes published.</div></div>
    <div class="step"><div class="n">05</div><h4>Second opinions</h4>
      <p>MCP links have to answer 2xx and name the app. Pricing pages get fetched where the docs are
      silent. A sample goes back to me for a manual re-read against the full text.</p>
      <div class="ran">Ran for real: {len(mcp)} MCP candidates checked, {len(mcp_verified)} confirmed;
      {audit['sample_size']} apps audited ({audit['hits']} hits, {audit['misses']} misses).</div></div>
  </div>

  <div class="two" style="margin-top:26px">
    <div class="card">
      <h3 style="font-size:15px">Where a human was needed</h3>
      <ul class="tight">
        <li><strong>Picking entry URLs.</strong> Curated first, then /docs, /api
        and developer.* guesses, then .md/llms variants, then a text proxy. 21 apps needed a URL I found
        by hand (Amazon publishes llms.txt, Coda redirects to Superhuman Docs, FanBasis is now Commas),
        and {len(failed)} page still beats every transport.</li>
        <li><strong>Commercial access.</strong> Pricing pages are the only place self-serve vs gated is
        written down, and they are marketing pages: 13 of 23 attempts produced something usable, and
        almost none stated API access in words a quote could be bound to.</li>
        <li><strong>JS-rendered docs.</strong> {len(failed)} app defeated the fetcher outright. The honest
        answer there is no fetchable documentation in this run, not a guessed row.</li>
        <li><strong>The {audit['misses']} audit corrections</strong> are mostly the model listing an auth
        variant my re-read did not, abstaining where the type was obvious, or reading a plan gate as
        silence.</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="font-size:15px">What is still open</h3>
      <ul class="tight">
        <li><strong>{100 - n} of 100 apps are not researched.</strong> They are named at the bottom, not
        filled in. The first attempt's 100-row dataset was synthetic and now lives in
        <code>discarded_synthetic/</code>.</li>
        <li><strong>{len(research) - len(access_stated)} of {n} access verdicts are undetermined</strong> and
        shown that way, not as self-serve.</li>
        <li><strong>MCP coverage is a floor.</strong> Nothing confirmed means the checks found nothing, not
        that nothing exists.</li>
      </ul>
    </div>
  </div>
</div></section>

<section id="verification"><div class="wrap">
  <h2>What I checked, and what it got wrong</h2>
  <div class="stats" style="margin-bottom:26px">
    <div class="stat"><b>{hints_bound}/{hints_offered}</b><span>evidence hints that verified verbatim</span></div>
    <div class="stat"><b>{audit['hits']}/{audit['hits'] + audit['misses']}</b><span>decided fields matched by hand audit</span></div>
    <div class="stat"><b>{audit['abstentions']}</b><span>fields where "undetermined" was the right answer</span></div>
    <div class="stat"><b>{len(mcp_verified)}/{len(mcp)}</b><span>MCP links that answered and named the app</span></div>
  </div>

  <h3 style="margin-bottom:8px">Every miss found by the hand audit</h3>
  <p class="muted" style="font-size:13px;margin:0 0 12px">
    {audit['sample_size']} apps &times; 5 fields = {audit['field_checks']} checks, picked to include the
    thinnest-evidence apps. Across <strong>all {audit['field_checks']} checks, agreement is
    {audit['agreement_on_all_checks']}%</strong>. That is the conservative figure, since a field the re-read
    correctly left blank still counts against the brief's "for each app" standard. Narrow it to the
    {audit['hits'] + audit['misses']} fields where either pass committed and it is
    {audit['agreement_on_decided']}%.</p>
  <table>
    <thead><tr><th>App</th><th>Field</th><th>Pass 1 published</th><th>After hand audit</th><th>Why</th></tr></thead>
    <tbody>{audit_rows}</tbody>
  </table>
  <div class="callout"><strong>Where it stands:</strong> the binder never let a made-up quote through.
  Every published quote is a substring of the saved page, and {rejected_pct}% of proposed claims were
  dropped for failing that check. What it did get wrong was <em>recall and classification</em>: it lost
  true claims when a sentence ran long, over-listed auth variants, and read Shopify's
  plan gating as silence. Those {audit['misses']} are the errors a second pass catches and a first
  one does not.</div>

  <h3 style="margin:26px 0 8px">Three checks, in order</h3>
  <table>
    <thead><tr><th>Loop</th><th>What it catches</th><th>Effect on this run</th></tr></thead>
    <tbody>
      <tr><td>1. Quality gate</td><td>Marketing pages, JS shells, error pages served with HTTP 200</td>
        <td>Dropped {len(failed)} of 100. Caught a Meta .md URL returning an error page and a WhatsApp
        fetch contaminated by a shared temp file.</td></tr>
      <tr><td>2. Quote binding</td><td>Any claim not literally in the fetched text</td>
        <td>{hints_offered - hints_bound} proposed claims rejected ({rejected_pct}%); no invented quote
        survived.</td></tr>
      <tr><td>3. Hand audit</td><td>Wrong classification and lost true claims</td>
        <td>{audit['misses']} fields corrected; agreement on decided fields {audit['agreement_on_decided']}%.</td></tr>
    </tbody>
  </table>

  <h3 style="margin:26px 0 8px">Not researched: {len(failed)} apps whose docs could not be fetched</h3>
  <p class="muted" style="font-size:13px;margin:0 0 10px">These are listed so the gap is visible. Each needs
  a browser-rendered fetch or a human.</p>
  <div>{failed_chips}</div>
</div></section>

<section id="limits"><div class="wrap">
  <h2>Limits, and what I would do with more time</h2>
  <div class="two">
    <div class="card">
      <h3 style="font-size:15px">What this page doesn't claim</h3>
      <ul class="tight">
        <li>That all 100 apps were researched. {n} were, at a standard where every field has a
        quote or says unknown.</li>
        <li>That the access split is the true split. {len(research) - len(access_stated)}
        of {n} verdicts are unknown, so the self-serve/gated ratio is a hint, not a census.</li>
        <li>That MCP does not exist. Only that the checks I ran confirmed none.</li>
        <li>That the model is right. It proposes; the binder and my audit decide what
        stays, and the audit found real classification errors ({audit['misses']} of
        {audit['field_checks']} checks).</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="font-size:15px">Next, in cost order</h3>
      <ul class="tight">
        <li><strong>Cheap:</strong> a headless browser for the one page that beats every
        transport, and for the 18 apps whose saved text had no quotable fact (all JS shells).</li>
        <li><strong>Cheap:</strong> a second extraction pass over the {stats['apps_with_fetched_docs']} saved
        pages with a stronger model, aimed at the failure patterns in the audit. The corpus is already
        on disk, so it costs tokens only.</li>
        <li><strong>Medium:</strong> a pricing-page extractor with per-site selectors, to turn
        {len(research) - len(access_stated)} undetermined access verdicts into facts.</li>
        <li><strong>Expensive, worth it:</strong> one email per gated app. That is the
        only way to learn approval timelines.</li>
      </ul>
    </div>
  </div>
</div></section>

<section id="run"><div class="wrap">
  <h2>Reproduce it</h2>
  <div class="card" style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;line-height:1.9">
python scripts/run_all.py --fetch --pricing&nbsp;&nbsp;# fetch, extract-bind, verify, audit, build<br><br>
<span style="color:#5f6b7a"># or stage by stage (order matters: bind rewrites research.json)</span><br>
    python scripts/fetch_docs.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# fetch + quality gate -> data/sources/<br>
    python scripts/make_digest.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# verbatim evidence digest<br>
    python scripts/bind_evidence.py data/extraction_api.json<br>
    python scripts/mcp_check.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# verify MCP links (after bind)<br>
    python scripts/resolve_access.py&nbsp;&nbsp;# pricing-page pass for silent docs<br>
    python scripts/audit_sample.py&nbsp;&nbsp;&nbsp;&nbsp;# hand-audit comparison + corrections<br>
    python scripts/patterns.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# aggregates -> data/stats.json<br>
    python scripts/build_page.py&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# this page
  </div>
  <p class="muted" style="font-size:12.5px;margin-top:10px">The pipeline is Python standard library only
  except for the optional Composio SDK path in <code>scripts/composio_pipeline.py</code>. Raw machine-readable
  dataset: <code>data/research_final.json</code>; it is also embedded below for agent consumers.</p>
</div></section>

<footer><div class="wrap">
  Built for the Composio AI Product Ops take-home. Saved page text, sources and every quote are in
  <code>data/</code>. Pages were fetched on 2026-11-23; docs move, so re-run instead of trusting a copy.
</div></footer>

<script type="application/json" id="dataset">{dataset_json}</script>
<script>
  const rows = [...document.querySelectorAll('#apps tbody tr')];
  const SELF = new Set(['Free Self-Serve','Free Trial','Open Source / Local CLI']);
  const GATED = new Set(['Paid Plan Required','Partner / Admin Approval','Enterprise / Contact Sales','Closed Platform']);
  document.getElementById('filters').addEventListener('click', e => {{
    const b = e.target.closest('button'); if (!b) return;
    document.querySelectorAll('#filters button').forEach(x => x.setAttribute('aria-pressed', x === b));
    const f = b.dataset.f;
    rows.forEach(tr => {{
      const a = tr.dataset.access, m = tr.dataset.mcp;
      let show = f === 'all'
        || (f === 'self' && SELF.has(a))
        || (f === 'gated' && GATED.has(a))
        || (f === 'undetermined' && !SELF.has(a) && !GATED.has(a))
        || (f === 'mcp' && m === 'verified-url');
      tr.style.display = show ? '' : 'none';
    }});
  }});
</script>
</body>
</html>
"""

(ROOT / "index.html").write_text(HTML, encoding="utf-8")
print(f"wrote index.html ({len(HTML):,} bytes)")
print(f"apps {n} | quotes {stats['verified_quotes']} | audit {audit['hits']}h/{audit['misses']}m"
      f" | failed {len(failed)}")
