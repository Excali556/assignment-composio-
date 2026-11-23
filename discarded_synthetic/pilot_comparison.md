# Pilot Calibration Report: 5 Benchmark Apps

## Overview
Before running the research agent on the full 100 apps, we tested and calibrated on a 5-app benchmark set representing the full spectrum of software distribution and access models:
1. **GitHub** (`#61`) - Developer Platform / Git Hosting (Standard OAuth2/PAT)
2. **Salesforce** (`#1`) - Enterprise CRM (OAuth2 Connected Apps with Developer Edition)
3. **Sherlock** (`#58`) - Open Source OSINT CLI (Local Python execution, no cloud API)
4. **Telegram** (`#27`) - Messaging / Bot API (HTTP Bot Token via BotFather)
5. **PitchBook** (`#90`) - Financial Market Intelligence (Enterprise Gated / Paywall)

---

## 1. Answer Key (Ground Truth)
Ground truth was established by manually reviewing official documentation, API reference guides, and GitHub repositories:
* [GitHub Answer Key Docs](https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api)
* [Salesforce Answer Key Docs](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_what_is_rest_api.htm)
* [Sherlock Answer Key Docs](https://github.com/sherlock-project/sherlock)
* [Telegram Answer Key Docs](https://core.telegram.org/bots/api)
* [PitchBook Answer Key Docs](https://pitchbook.com/products/research-api)

---

## 2. Accuracy Comparison: Run 1 vs. Run 2

| App | Category | Run 1 Score (Untuned) | Run 2 Score (Tuned) | Main Improvement |
| :--- | :--- | :---: | :---: | :--- |
| **GitHub** | Developer, Infra | 6/7 (85.7%) | **7/7 (100.0%)** | Correctly categorized fine-grained PAT as OAuth2/Bearer; added GraphQL. |
| **Salesforce** | CRM and Sales | 4/7 (57.1%) | **7/7 (100.0%)** | Targeted `developer.salesforce.com` discovering free permanent Developer Edition; found official CLI MCP. |
| **Sherlock** | Data, SEO & Scraping | 2/7 (28.6%) | **7/7 (100.0%)** | Eliminated hallucinated REST API/pricing. Classified as CLI tool with community MCP wrapper. |
| **Telegram** | Communications | 7/7 (100.0%) | **7/7 (100.0%)** | Stable high performance on Bot API and BotFather token model. |
| **PitchBook** | Finance and Fintech | 4/7 (57.1%) | **7/7 (100.0%)** | Differentiated demo marketing from API access; identified Enterprise contract gate. |
| **TOTAL** | **Benchmark Overall** | **23/35 (65.7%)** | **35/35 (100.0%)** | **+34.3% Accuracy Gain** |

---

## 3. Error Taxonomy & Systematic Fixes

| Error Type | Affected App(s) | Root Cause in Run 1 | Systematic Fix Implemented |
| :--- | :--- | :--- | :--- |
| **Wrong Source Domain** | Salesforce | Agent scraped `salesforce.com/editions-pricing` instead of `developer.salesforce.com`. | Domain filtering prioritized `developer.*`, `docs.*`, `api.*`, and developer portals over marketing landing pages. |
| **SaaS Hallucination on CLI Tools** | Sherlock | Agent assumed every app has a SaaS REST API and invented subscription plans & endpoints. | Introduced explicit rule for Open Source repositories & CLI tools: `auth="None"`, `api_types=["CLI / Local Execution"]`, `buildable="Partial"`. |
| **Marketing Trap (Demo vs. API)** | PitchBook | Agent mistook "Request a free demo" button on landing page for self-serve developer access. | Introduced strict verification rule: access is only "Free Self-Serve" or "Free Trial" if instant credentials can be obtained without sales rep contact. |
| **Developer Sandbox Blindness** | Salesforce | Looked at commercial enterprise pricing, missing that developer sandboxes are 100% free. | Added rule to check for dedicated Developer Edition / Sandbox tiers before declaring a platform "Paid Plan Required". |
| **Generic Auth Oversimplification** | GitHub | Labeled Personal Access Tokens as generic "API Key", missing OAuth scopes and Bearer header. | Clarified distinction between static API Keys and OAuth2 / Bearer Tokens. |

---

## 4. Adversarial Quote Verification Check
The deterministic quote verifier (`scripts/quote_verifier.py`) was tested against:
1. **Real verbatim docs quotes**: Confirmed exact substring match (Score: 1.0).
2. **Planted adversarial hallucination**: Injected `"GitHub requires a corporate credit card and $500 monthly fee to generate REST API tokens."` into GitHub record.
   * **Result**: `quote_verifier.py` flagged the planted quote as `Passed=False, Msg=Quote not found in source text (Planted or Hallucinated)`.
3. **Honest "unknown" handling**: Permitted without penalty to prevent guessing.
