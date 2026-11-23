# Page: AI Product Ops Intern -The take-home assignment

  Primary filter. Budget 6-8 hours; we care about the result and how clearly you present it, not hours spent so better to submit as early as possible (<8 hrs after receiving)

  ### Context

  Composio turns apps into tools that AI agents can call. Before we build a toolkit for an app, we research it: what auth it uses, whether there is a self-serve path or it is partner-gated, what the API surface looks like, and whether it can be an MCP server or agent-callable skills. We do this across hundreds of apps. Doing it by hand does not scale. This assignment is a small, real version of that problem.

  ### The task

  You are given a list of 100 apps (below). For each, research and capture:

  * Category and what it does in one line.

  * Auth method(s): OAuth2, API key, Basic, token, or other.

  * Self-serve vs gated: can a developer get credentials themselves for free or on a trial, or does it need a paid plan, admin approval, or a partnership / contact-sales gate.

  * API surface: documented public REST / GraphQL, roughly how broad, and any existing MCP.

  * Buildability verdict: could this be an agent toolkit today, and the main blocker if not.

  * Evidence: the docs URL / article behind each answer.

  * and more..

  Then, the actual point:

  * Find the patterns. Do not just produce 100 rows. Cluster the results and tell us what patterns you see (which auth dominates, which categories are self-serve vs gated, the most common blocker, where the easy wins are versus what needs outreach). Insight over raw table.

  * Do it with an agent, not by hand. Build an agent (or script / pipeline) that does the research across the 100. Using Composio's own SDK and MCP to build it is in the spirit of the role. Tell us what it does and where it needed a human.

  * Verify your accuracy. Sample the 100, cross-check your agent's answers against real docs by hand, and report where it was right and wrong. Show how you know the findings are trustworthy. Build real verification loops (agent, browser-use, and other means) plus human checks, and show at the end how it was verified, including how accuracy moved from a lower first pass to a higher one because of those loops. Accuracy is what matters most.

  ### The deliverable: a single self-explanatory HTML page or slideshow

  Everything above must be one HTML page / Case Study a reviewer understands in about two minutes with no narration. It must make clear on its own: the findings (clean skimmable table/matrix), the patterns (up top, plainly stated, the headline), the agent (what you built, where a human was needed), the proof (the app you built, live link or runnable trigger), and the verification (accuracy check on a sample, hits and misses shown honestly). Clarity and presentation are the point. Show both the final output and the process/workflow behind it, and make it easy for both an agent and a human to consume.

  ### Constraints and honesty

  * Use AI tooling freely (that is the job), but understand and be able to explain everything you submit; the interview will probe it.

  * If the agent got things wrong or an app defeated you, say so on the page.

  * You do not need paid accounts for apps. Where an app is gated behind payment or partnership, saying so with evidence is the correct finding, not a failure.

  ### What to submit

  * A live link to the deployed HTML page/ Case study.

  * A link to the source repo with a short README on how to run the research agent.

  ---

  ## The 100 apps (research set)

  A real mix: apps customers have actually requested, and well-known apps. Across 10 categories and every common auth pattern on purpose, so the interesting part is the patterns across all 100.

  ### 1. CRM and Sales

  ### 2. Support and Helpdesk

  ### 3. Communications and Messaging

  ### 4. Marketing, Ads, Email and Social

  ### 5. Ecommerce

  ### 6. Data, SEO and Scraping

  ### 7. Developer, Infra and Data platforms

  ### 8. Productivity and Project Management

  ### 9. Finance and Fintech

  ### 10. AI, Research and Media-native

  ---