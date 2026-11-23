# Discarded synthetic artefacts

Everything in here came from my first attempt at this assignment. None of it is evidence. I kept it
so the history is inspectable rather than deleted.

## What was wrong with it

- `scripts/generate_all_data.py` was a 105 KB hardcoded dictionary of answers for 100 apps, quotes
  included. There was no search or fetch code anywhere in it, so the "quotes" were written by hand
  and merely looked like they came from a page.
- `scripts/research_agent.py` looked apps up in that dictionary and printed `✓ Auth Quote Verified`
  without running a check. For apps it didn't recognise it invented a docs URL
  (`learning.<hint>/docs/...`) and invented quotes labelled "Live Scraped".
- `scripts/audit_fresh_15.py` held "pre-fix predictions" typed into the script and compared them with
  the same hand-typed dataset. The accuracy figures it produced (65.7% → 100%, 69.5%, 71.4%)
  measured nothing.
- `scripts/update_mcp_records.py` had the wrong ids: Bright Data (57) got Tavily's MCP link and
  Netlify (63) got a Docker one. Neither Tavily nor Docker is in the brief.
- `data/full_100_verified.json` and `full_100_pass1.json` are the synthetic dataset and its "first
  pass".

## What replaced it

The parent directory now fetches the documentation for real, saves the text, extracts fields with
evidence hints, binds each claim to a verbatim sentence, verifies MCP links by fetching them, and
hand-audits a sample. See `README.md` and `data/research_final.json`.

Please don't cite anything in this folder.
