# Can any of these 100 apps become an agent toolkit today?

My submission for the Composio AI Product Ops take-home. The pipeline fetches each app's developer
documentation, pulls out auth / access / API facts with a real model, and publishes a claim only if
it can point at the sentence the claim came from. Where the page says nothing, the row says nothing.

Worth opening first:

- `index.html` — the deliverable. One file, no CDN, no build step.
- `data/research_final.json` — the same data in machine-readable form.
- `data/sources/<id>.txt` — the fetched page text, untouched. Every quote on the page is a substring
  of one of these files.

The page header carries the candidate name, a link to this repo and the date the pages were fetched.

## Where the numbers came from

| | |
|---|---|
| Docs fetched | 99 of 100, saved with URL, status, transport and timestamp |
| Apps researched | 99 |
| Claims with a verified quote | 186 |
| Fields determined | 45.5% (180 of 396); the rest say `Not Stated` |
| Hand audit | 25 apps × 5 fields = 125 checks: 41 matched, 24 missed, 60 correct abstentions |
| Accuracy | 32.8% across all 125 checks, 63.1% where either pass committed |
| Extraction | Groq `openai/gpt-oss-120b` for 81 apps, `openai/gpt-oss-20b` for the last 18 after the 120b daily cap |
| MCP | 11 of 17 candidates confirmed by fetching them |
| Missing | #84 Paygent Connect. Named on the page, row left empty |

Read 32.8% first, because it's the conservative figure. Most of the disagreement isn't invented fact:
the model lists more auth variants than my re-read did, or it stays quiet where the API type was
obvious. Where the re-read turned up a real error, its value replaced the model's in
`data/research_final.json`, and the page lists all 24 cases with what changed and why.

Three other things worth knowing before you read the results:

1. The audit number is low because the brief asks for a fact on every field. A field that was
   correctly left blank still counts as a miss there.
2. "None confirmed" for MCP means the checks I ran found nothing, not that nothing exists.
3. Access is mostly undetermined on purpose. 82 of 99 apps never state a commercial access model on
   a page I could fetch, and that is itself the finding.

## What the data shows

The bottleneck is documentation, not gating. Only 17 of 99 apps state an access model on a page the
pipeline could read: 10 self-serve, 6 gated, 1 mixed. The other 82 say nothing.

Token auth is the default wherever auth is documented. 59 apps document it; 31 use OAuth2 and 15 a
bearer or bot token (13 more spell out "Bearer Token"). API keys appear in 32 and HTTP Basic in 4,
and Basic is usually just how the key travels.

MCP is still the exception. 11 endpoints answered and named the app, 4 more are advertised in docs
with no URL I could resolve, and 84 had nothing. Room to be first, but weak evidence of absence.

Two apps need a different build entirely: Sherlock and Mermaid CLI ship as command-line tools with no
hosted HTTP API, so a toolkit there means wrapping the binary in a container.

## The pipeline

```
scripts/fetch_docs.py     fetch docs (urllib -> curl -> r.jina.ai text proxy) + .md/llms variants
                          + quality gate; 21 hand-curated fallback URLs
scripts/make_digest.py    pull verbatim decision-relevant sentences per app
scripts/extract.py        model extraction -> fields + short evidence hints   [needs a key]
scripts/bind_evidence.py  locate each hint in the saved page, expand to a sentence,
                          re-check it verbatim, demote fields whose evidence fails
scripts/mcp_check.py      fetch candidate MCP endpoints; keep only 2xx pages naming the app
scripts/resolve_access.py fetch pricing pages for apps whose docs are silent
scripts/audit_sample.py   human re-read vs pass 1 -> corrections + accuracy
scripts/patterns.py       aggregates -> data/stats.json
scripts/build_page.py     render index.html from the data files
```

The quality gate is what makes the corpus usable. A page only counts if it names the app, contains
both API and auth language, and isn't an error page in its first 2.5k characters. It rejected 1 of
100: a docs host serving a 287k-character page that never names the app.

## The model run

`scripts/extract.py` sends the saved page text (condensed to the ~6k characters that carry signal) to
an OpenAI-compatible endpoint and asks for fields plus a short hint phrase for each. It never asks for
a quote. `bind_evidence.py` writes the quote afterwards, and only if the sentence is a verbatim
substring of the saved page.

```bash
cp .env.example .env                  # GROQ_API_KEY=...  (or OPENAI_API_KEY=...)
set -a; . ./.env; set +a
python scripts/extract.py --workers 4 --retry-failed    # ~25 min on Groq's free tier
```

Free-tier limits were worked with rather than around: a shared token bucket paces requests, 429
backoffs are honoured, and a 413 shrinks the prompt. When the 120b daily cap hit with 18 apps left, I
resumed on `gpt-oss-20b`. Every record carries `extracted_by`, and the page names both models.

## Running it

```bash
python scripts/run_all.py               # rebuild everything from saved sources (~20s)
python scripts/run_all.py --fetch       # also re-fetch all 100 docs pages (~80s)
python scripts/run_all.py --extract     # also re-run the model extraction (needs a key, ~25min)
open index.html
```

Stage order matters. `bind_evidence.py` rewrites `data/research.json`, so `mcp_check.py` has to run
after it. `run_all.py` enforces that; running the stages by hand in the wrong order drops the verified
MCP links and quietly changes the audit numbers. I hit exactly that bug during the build.

Python 3.10+ and the system `curl` binary. There is nothing to install: the pipeline is standard
library only, which is why there is no `requirements.txt`.

## Deploying

`index.html` is self-contained, so it goes to Vercel as a plain static site with no build step:

```bash
vercel --prod
```

`.vercelignore` keeps the upload to the page itself, and `vercel.json` turns on clean URLs. If you use
the dashboard instead, pick any static preset and leave the build command empty.

## Layout

```
apps.csv                     the brief's 100 apps
index.html                   the deliverable (generated)
.env                         model key, gitignored, never committed
data/sources/<id>.txt        saved page text, verbatim (the evidence)
data/sources/<id>.meta.json  URL, status, transport, timestamp for each fetch
data/fetch_manifest.json     what was fetched, what failed and why
data/extraction_api.json     model output: fields + evidence hints (pass 1)
data/research.json           pass 1 after binding
data/audit_pass2.json        hand re-read of 25 apps
data/research_final.json     final dataset (audit corrections applied)
data/audit_result.json       hits, misses, abstentions, both accuracy figures
data/stats.json              aggregates used by the page
data/mcp_verified.json       MCP candidates and what answered
discarded_synthetic/         the first attempt's fabricated dataset (kept, not cited)
```

One saved page reproduces the example tokens Discord prints in its own docs (a bot token, a bearer token
and a Basic header). Those three strings are replaced with `REDACTED_...` in `data/sources/26.txt` and
`data/digest.*`, because GitHub's push protection refuses any repo containing them. No published quote
contains any of them, so nothing on the page is affected.

## What changed from the first attempt

The first version of this repo shipped a 100-row dataset whose "verbatim quotes" were typed into a
generator script, an agent that printed `✓ Quote Verified` without checking anything, and accuracy
figures that compared one hand-typed set against another. All of it went to `discarded_synthetic/`.
What replaced it: real fetches for 99 apps, a real model run whose quotes are bound and re-checked,
and an accuracy figure that is unflattering on purpose.
