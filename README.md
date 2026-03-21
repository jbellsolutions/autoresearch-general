# Autoresearch — General-Purpose Self-Improving Optimization

Based on the [Karpathy autoresearch pattern](https://github.com/karpathy/autoresearch). While the original optimizes LLM training code and [autoresearch-diagrams](https://www.youtube.com/watch?v=qKU-e0x2EmE) optimizes diagram prompts, this version works for **any task** with measurable output quality.

![Pattern](https://img.shields.io/badge/pattern-generate→evaluate→keep%2Fdiscard→mutate→repeat-blue)

## The Pattern

```
LOOP FOREVER:
  1. Generate N variations using current best prompt
  2. Score each against user-defined criteria (1-10)
  3. Keep if batch score improves, discard if not
  4. Mutate the prompt targeting weakest criteria
  5. Log everything → repeat
```

You define what to optimize and how to score it. The system evolves the prompt itself.

## Use Cases

- **Cold email copy** — optimize subject lines, body copy, CTAs
- **LinkedIn outreach** — connection requests, DMs, comment hooks
- **Sales scripts** — call openers, objection handling, closing lines
- **Landing page copy** — headlines, hero text, value propositions
- **Content hooks** — social media post openers, video intros
- **Prompt engineering** — any prompt you want to systematically improve
- **Code generation** — optimize code-gen prompts for quality/correctness

## Quick Start

### As a Claude Code Skill (Recommended)

```bash
# Install as a skill
git clone https://github.com/jbellsolutions/autoresearch-general.git ~/.claude/skills/autoresearch-general

# Then in any Claude Code session:
/autoresearch
```

Tell it what to optimize:
- "Optimize my cold email subject lines for SaaS founders"
- "Improve my LinkedIn connection request messages"
- "Optimize my sales call opening script"

### As a Standalone Script

```bash
# Install dependencies
pip install anthropic python-dotenv

# Set your API key
export ANTHROPIC_API_KEY="your-key"

# Interactive setup
python3 autoresearch.py --setup

# Run a single cycle (test)
python3 autoresearch.py --once

# Run 10 cycles
python3 autoresearch.py --cycles 10

# Run continuously (leave it overnight)
python3 autoresearch.py
```

## Setup Questions

When you run setup, you'll configure 4 things:

1. **What are you optimizing?** — The task description
2. **Eval criteria** — Up to 5 criteria, each scored 1-10
3. **Batch size** — Variations per cycle (default 5)
4. **Starting prompt** — Your initial approach to improve from

## Example Run

```
🔬 AUTORESEARCH — Cold email to SaaS founders about AI agent deployment
   Criteria: ['persuasiveness', 'personalization', 'brevity', 'conversion_potential']
   Batch size: 5

============================================================
RUN 1 | Best score: 0.0/40
============================================================
  Generating 5 variations...
  Evaluating against 4 criteria...
  Scores by criterion:
    persuasiveness      : 6.2/10 ██████░░░░
    personalization     : 5.8/10 █████░░░░░
    brevity             : 7.1/10 ███████░░░
    conversion_potential: 5.4/10 █████░░░░░

  ✅ KEPT — 24.5 > 0.0 (+24.5)
  Mutating prompt...

============================================================
RUN 2 | Best score: 24.5/40
============================================================
  ...
  ✅ KEPT — 28.3 > 24.5 (+3.8)

============================================================
RUN 3 | Best score: 28.3/40
============================================================
  ...
  ❌ DISCARDED — 26.1 ≤ 28.3
```

## File Structure

```
autoresearch-general/
  SKILL.md              # Claude Code skill definition
  autoresearch.py       # Main generate → eval → mutate loop
  README.md             # This file
  requirements.txt      # Python dependencies
  data/                 # Created at runtime
    config.json         # Task config
    prompt.txt          # Current prompt being optimized
    best_prompt.txt     # Best prompt found so far
    state.json          # Loop state
    results.jsonl       # Experiment log
    outputs/
      run_001/          # Generated outputs per run
      run_002/
```

## How Mutation Works

After each evaluation cycle:

1. **Identify weakest criteria** — which scored lowest on average?
2. **Find failure patterns** — what do low-scoring variations have in common?
3. **Targeted rewrite** — modify the prompt to specifically address weak areas
4. **Preserve strengths** — don't lose what's working well
5. **One major change per mutation** — isolate variables to know what worked

## Cost

- ~$0.01-0.03 per evaluation (Claude scoring text outputs)
- ~$0.01 per mutation (prompt rewriting)
- **~$0.05-0.15 per cycle** (5 variations)
- At continuous running: ~$3-9/hour
- Overnight (8hrs): ~$24-72

## The Karpathy Autoresearch Family

| Repo | Optimizes | Metric | Requires |
|------|-----------|--------|----------|
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | LLM training code | val_bpb | NVIDIA GPU |
| [autoresearch-diagrams](https://mcpmarket.com/tools/skills/autoresearch-diagrams) | Diagram prompts | Vision score | Gemini + Claude API |
| **autoresearch-general** (this repo) | Any text/prompt | User-defined criteria | Claude API |

## License

MIT
