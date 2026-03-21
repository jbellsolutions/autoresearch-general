---
name: autoresearch
description: General-purpose self-improving optimization using the Karpathy autoresearch pattern. Works for any task with measurable output — sales copy, outreach, prompts, content, code, emails, landing pages. Generate → Evaluate → Keep/Discard → Mutate → Repeat.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebFetch, WebSearch
---

# Autoresearch — General-Purpose Self-Improving Optimization

## What It Does

Applies the Karpathy autoresearch pattern to **any task** where output quality can be scored. The core loop:

1. **Generate** N variations of the output using the current best prompt/approach
2. **Evaluate** each against user-defined criteria (scored 1-10 per criterion)
3. **Keep** if the batch score beats the current best, **discard** otherwise
4. **Mutate** the winning prompt/approach based on failure analysis
5. **Log** everything to JSONL for tracking
6. **Repeat** indefinitely until stopped

## How To Use

When the user invokes `/autoresearch`, ask them 4 questions:

### 1. What are you optimizing?
Examples:
- "Cold email subject lines for SaaS founders"
- "LinkedIn outreach messages for AI agency leads"
- "Landing page hero copy for 10XVA"
- "Python function to parse CSV files"
- "Sales call opening scripts"
- "Social media post hooks"

### 2. What are your eval criteria? (up to 5)
Each criterion gets scored 1-10. Examples:
- **Persuasiveness** — does it compel action?
- **Clarity** — is the message instantly clear?
- **Personalization** — does it feel custom, not templated?
- **Brevity** — is it concise without losing impact?
- **Brand voice** — does it match the desired tone?
- **Technical accuracy** — is the code/info correct?
- **Conversion potential** — would this get a reply/click?

### 3. How many variations per batch?
Default: 5 (good balance of exploration vs cost). Range: 3-10.

### 4. Starting prompt/approach
The initial version to optimize from. Can be:
- An existing prompt they want to improve
- A sample output they want to beat
- A blank slate (you'll generate a baseline)

## The Loop

Once configured, run this loop:

```
SETUP:
- Save config to data/config.json
- Save initial prompt to data/prompt.txt
- Initialize data/state.json with {run: 0, best_score: 0}
- Create data/results.jsonl (empty)

LOOP:
1. Read current prompt from data/prompt.txt
2. Generate N variations using the prompt
3. Score each variation against all criteria (1-10 per criterion)
4. Calculate batch_score = average of all scores across all variations
5. Read best_score from data/state.json

IF batch_score > best_score:
  - Save prompt to data/best_prompt.txt
  - Update state.json with new best_score and run number
  - Status: KEEP
  - Print: "✅ Run {N}: {batch_score:.1f} > {best_score:.1f} — KEPT"
ELSE:
  - Revert to data/best_prompt.txt
  - Status: DISCARD
  - Print: "❌ Run {N}: {batch_score:.1f} ≤ {best_score:.1f} — DISCARDED"

6. Analyze failures: which criteria scored lowest? What patterns in low-scoring variations?
7. Mutate the best prompt: rewrite with specific improvements targeting weak criteria
8. Save mutated prompt to data/prompt.txt
9. Append run results to data/results.jsonl
10. Increment run counter
11. GOTO 1
```

## File Structure

```
~/.claude/skills/autoresearch-general/
  SKILL.md              # This file
  data/
    config.json         # Task config (what, criteria, batch_size)
    prompt.txt          # Current prompt being optimized
    best_prompt.txt     # Best prompt found so far
    state.json          # Loop state {run, best_score, total_runs, kept, discarded}
    results.jsonl       # Append-only experiment log
    outputs/
      run_001/          # Generated outputs per run
      run_002/
      ...
```

## Mutation Strategy

When mutating the prompt after evaluation, follow this strategy:

1. **Identify weakest criteria** — which scored lowest on average?
2. **Find failure patterns** — what do low-scoring variations have in common?
3. **Targeted rewrite** — modify the prompt to specifically address weak areas
4. **Preserve strengths** — don't lose what's working well
5. **One major change per mutation** — don't change everything at once (isolate variables)

## Example: Cold Email Optimization

```
Config:
  task: "Cold email to SaaS founders about AI agent deployment"
  criteria: [persuasiveness, personalization, brevity, conversion_potential]
  batch_size: 5

Run 1 (Baseline): Score 24.3/40 — KEPT
Run 2 (Shorter subject lines): Score 26.1/40 — KEPT
Run 3 (Added social proof): Score 25.8/40 — DISCARDED
Run 4 (Question-based opening): Score 28.4/40 — KEPT
Run 5 (Personalized pain points): Score 31.2/40 — KEPT
...
```

## Example: LinkedIn Outreach Optimization

```
Config:
  task: "LinkedIn connection request message for AI influencer leads"
  criteria: [authenticity, value_proposition, curiosity_hook, reply_likelihood, brevity]
  batch_size: 5

Run 1 (Baseline): Score 28.0/50 — KEPT
Run 2 (Lead with their content): Score 33.5/50 — KEPT
Run 3 (Mutual connection angle): Score 31.2/50 — DISCARDED
Run 4 (Specific value offer): Score 36.8/50 — KEPT
...
```

## Key Principles

1. **NEVER STOP** — keep looping until manually interrupted. The user may be away.
2. **Log everything** — every run, every score, every mutation goes to results.jsonl
3. **One change at a time** — isolate variables so you know what worked
4. **Preserve winners** — best_prompt.txt is the safety net
5. **Score honestly** — don't inflate scores. Be a harsh critic.
6. **Think like a researcher** — form hypotheses about why things work/don't

## Cost Estimate
- ~$0.01-0.03 per evaluation (Claude scoring text outputs)
- ~$0.01 per mutation (prompt rewriting)
- ~$0.05-0.15 per cycle (5 variations)
- At continuous running: ~$3-9/hour

## Adaptation Notes

This skill is the **generalized version** of the Karpathy autoresearch pattern:
- Original (Karpathy): optimizes LLM training code, measures val_bpb
- Diagrams (Saraev): optimizes diagram prompts, measures visual quality
- **This version**: optimizes ANY text/prompt output, measures user-defined criteria

The pattern is universal: **generate → evaluate → keep/discard → mutate → repeat**.
