#!/usr/bin/env python3
"""
General-purpose autoresearch runner.
Implements the Karpathy autoresearch pattern for any text optimization task.

Usage:
  python3 autoresearch.py --setup          # Interactive setup
  python3 autoresearch.py --once           # Single cycle
  python3 autoresearch.py --cycles 10      # Run N cycles
  python3 autoresearch.py                  # Run continuously
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package required. Install with: pip install anthropic")
    sys.exit(1)

DATA_DIR = Path(__file__).parent / "data"
CONFIG_FILE = DATA_DIR / "config.json"
PROMPT_FILE = DATA_DIR / "prompt.txt"
BEST_PROMPT_FILE = DATA_DIR / "best_prompt.txt"
STATE_FILE = DATA_DIR / "state.json"
RESULTS_FILE = DATA_DIR / "results.jsonl"
OUTPUTS_DIR = DATA_DIR / "outputs"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path, default=None):
    if path.exists():
        return json.loads(path.read_text())
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))


def append_jsonl(path, record):
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def setup_interactive():
    """Interactive setup to configure what to optimize."""
    ensure_dirs()
    print("\n=== AUTORESEARCH SETUP ===\n")

    task = input("What are you optimizing?\n> ").strip()
    print("\nEnter eval criteria (1-10 score each). Enter blank line when done:")
    criteria = []
    while True:
        c = input(f"  Criterion {len(criteria)+1}: ").strip()
        if not c:
            break
        criteria.append(c)
    if not criteria:
        criteria = ["quality", "clarity", "effectiveness"]
        print(f"  Using defaults: {criteria}")

    batch_str = input(f"\nVariations per batch (default 5): ").strip()
    batch_size = int(batch_str) if batch_str else 5

    print("\nEnter your starting prompt/approach (enter blank line when done):")
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    initial_prompt = "\n".join(lines) if lines else f"Generate a high-quality {task}"

    config = {
        "task": task,
        "criteria": criteria,
        "batch_size": batch_size,
        "created": datetime.now().isoformat(),
    }
    save_json(CONFIG_FILE, config)
    PROMPT_FILE.write_text(initial_prompt)
    BEST_PROMPT_FILE.write_text(initial_prompt)
    save_json(STATE_FILE, {"run": 0, "best_score": 0, "kept": 0, "discarded": 0})

    print(f"\n✅ Setup complete!")
    print(f"   Task: {task}")
    print(f"   Criteria: {criteria}")
    print(f"   Batch size: {batch_size}")
    print(f"   Config saved to: {CONFIG_FILE}")


def generate_variations(client, prompt, task, batch_size):
    """Generate N variations using the current prompt."""
    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"""You are a creative variation generator. Your task:

TASK: {task}

APPROACH/PROMPT TO USE:
{prompt}

Generate exactly {batch_size} distinct variations. Each should follow the approach but be meaningfully different.
Number them 1-{batch_size}. Separate each with "---VARIATION---".

Output ONLY the variations, no commentary."""
        }]
    )
    text = response.content[0].text
    # Split on the separator, clean up
    parts = text.split("---VARIATION---")
    if len(parts) == 1:
        # Try splitting on numbered patterns
        import re
        parts = re.split(r'\n(?=\d+[\.\)]\s)', text)
    variations = [p.strip() for p in parts if p.strip()]
    return variations[:batch_size]


def evaluate_variations(client, variations, task, criteria):
    """Score each variation against all criteria."""
    criteria_str = "\n".join(f"- {c}" for c in criteria)
    max_score = len(criteria) * 10

    scores = []
    for i, var in enumerate(variations):
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""You are a harsh but fair evaluator. Score this output for the task.

TASK: {task}

OUTPUT TO EVALUATE:
{var}

CRITERIA (score each 1-10, where 1=terrible, 5=mediocre, 10=exceptional):
{criteria_str}

Respond in ONLY this JSON format, no other text:
{{"scores": {{{", ".join(f'"{c}": <score>' for c in criteria)}}}, "reasoning": "<one sentence>"}}"""
            }]
        )
        try:
            text = response.content[0].text.strip()
            # Extract JSON from response
            if "```" in text:
                text = text.split("```")[1].strip()
                if text.startswith("json"):
                    text = text[4:].strip()
            result = json.loads(text)
            result["variation_index"] = i
            result["variation_text"] = var[:200]  # truncate for logging
            scores.append(result)
        except (json.JSONDecodeError, IndexError):
            # Fallback: assign neutral scores
            scores.append({
                "scores": {c: 5 for c in criteria},
                "reasoning": "Failed to parse evaluation",
                "variation_index": i,
                "variation_text": var[:200],
            })

    return scores


def mutate_prompt(client, prompt, task, criteria, eval_results, best_score):
    """Mutate the prompt based on evaluation results."""
    # Find weakest criteria
    criteria_avgs = {}
    for c in criteria:
        vals = [e["scores"].get(c, 5) for e in eval_results]
        criteria_avgs[c] = sum(vals) / len(vals) if vals else 5

    weakest = sorted(criteria_avgs.items(), key=lambda x: x[1])[:2]
    weakest_str = ", ".join(f"{k} (avg {v:.1f})" for k, v in weakest)

    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""You are a prompt optimization expert. Improve this prompt.

TASK: {task}
CURRENT BEST SCORE: {best_score:.1f}

CURRENT PROMPT:
{prompt}

WEAKEST CRITERIA: {weakest_str}

EVALUATION FEEDBACK:
{json.dumps([{"reasoning": e["reasoning"], "scores": e["scores"]} for e in eval_results], indent=2)}

Rules:
1. Make ONE targeted improvement addressing the weakest criteria
2. Preserve what's already working well
3. Be specific and concrete in your instructions
4. Don't make the prompt longer than necessary

Output ONLY the improved prompt, no commentary or explanation."""
        }]
    )
    return response.content[0].text.strip()


def run_cycle(client, config, run_num):
    """Execute one generate→evaluate→keep/discard→mutate cycle."""
    task = config["task"]
    criteria = config["criteria"]
    batch_size = config["batch_size"]
    max_score = len(criteria) * 10

    prompt = PROMPT_FILE.read_text()
    state = load_json(STATE_FILE)
    best_score = state.get("best_score", 0)

    print(f"\n{'='*60}")
    print(f"RUN {run_num} | Best score: {best_score:.1f}/{max_score}")
    print(f"{'='*60}")

    # 1. Generate
    print(f"  Generating {batch_size} variations...")
    variations = generate_variations(client, prompt, task, batch_size)
    print(f"  Generated {len(variations)} variations")

    # Save outputs
    run_dir = OUTPUTS_DIR / f"run_{run_num:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    for i, var in enumerate(variations):
        (run_dir / f"variation_{i+1:02d}.txt").write_text(var)

    # 2. Evaluate
    print(f"  Evaluating against {len(criteria)} criteria...")
    eval_results = evaluate_variations(client, variations, task, criteria)

    # Calculate batch score
    all_scores = []
    for e in eval_results:
        all_scores.extend(e["scores"].values())
    batch_score = sum(all_scores) / len(all_scores) if all_scores else 0
    batch_total = batch_score * len(criteria)  # scale to total

    # Per-criteria averages
    criteria_avgs = {}
    for c in criteria:
        vals = [e["scores"].get(c, 5) for e in eval_results]
        criteria_avgs[c] = sum(vals) / len(vals) if vals else 5

    print(f"  Scores by criterion:")
    for c, avg in criteria_avgs.items():
        bar = "█" * int(avg) + "░" * (10 - int(avg))
        print(f"    {c:20s}: {avg:.1f}/10 {bar}")

    # 3. Keep or discard
    if batch_total > best_score:
        BEST_PROMPT_FILE.write_text(prompt)
        state["best_score"] = batch_total
        state["kept"] = state.get("kept", 0) + 1
        status = "keep"
        print(f"\n  ✅ KEPT — {batch_total:.1f} > {best_score:.1f} (+{batch_total - best_score:.1f})")
    else:
        # Revert to best
        prompt = BEST_PROMPT_FILE.read_text()
        state["discarded"] = state.get("discarded", 0) + 1
        status = "discard"
        print(f"\n  ❌ DISCARDED — {batch_total:.1f} ≤ {best_score:.1f}")

    # 4. Mutate
    print(f"  Mutating prompt...")
    new_prompt = mutate_prompt(client, prompt, task, criteria, eval_results, max(best_score, batch_total))
    PROMPT_FILE.write_text(new_prompt)

    # 5. Log
    state["run"] = run_num
    save_json(STATE_FILE, state)

    record = {
        "run": run_num,
        "timestamp": datetime.now().isoformat(),
        "batch_score": batch_total,
        "best_score": state["best_score"],
        "status": status,
        "criteria_scores": criteria_avgs,
        "num_variations": len(variations),
        "prompt_preview": new_prompt[:200],
    }
    append_jsonl(RESULTS_FILE, record)

    return status, batch_total


def main():
    parser = argparse.ArgumentParser(description="General-purpose autoresearch")
    parser.add_argument("--setup", action="store_true", help="Interactive setup")
    parser.add_argument("--once", action="store_true", help="Single cycle")
    parser.add_argument("--cycles", type=int, default=0, help="Run N cycles")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between cycles (default 30)")
    args = parser.parse_args()

    if args.setup:
        setup_interactive()
        return

    # Verify setup
    if not CONFIG_FILE.exists():
        print("ERROR: No config found. Run with --setup first.")
        sys.exit(1)

    config = load_json(CONFIG_FILE)
    state = load_json(STATE_FILE, {"run": 0})
    client = anthropic.Anthropic()

    print(f"\n🔬 AUTORESEARCH — {config['task']}")
    print(f"   Criteria: {config['criteria']}")
    print(f"   Batch size: {config['batch_size']}")
    print(f"   Starting from run {state['run']}")

    if args.once:
        run_cycle(client, config, state["run"] + 1)
    elif args.cycles > 0:
        for i in range(args.cycles):
            state = load_json(STATE_FILE)
            run_cycle(client, config, state["run"] + 1)
            if i < args.cycles - 1:
                print(f"\n  ⏳ Waiting {args.interval}s before next cycle...")
                time.sleep(args.interval)
    else:
        # Continuous mode
        print(f"\n   Running continuously (Ctrl+C to stop)...")
        try:
            while True:
                state = load_json(STATE_FILE)
                run_cycle(client, config, state["run"] + 1)
                print(f"\n  ⏳ Waiting {args.interval}s before next cycle...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            state = load_json(STATE_FILE)
            print(f"\n\n🛑 Stopped after {state['run']} runs")
            print(f"   Best score: {state['best_score']:.1f}")
            print(f"   Kept: {state.get('kept', 0)} | Discarded: {state.get('discarded', 0)}")
            print(f"   Best prompt saved to: {BEST_PROMPT_FILE}")


if __name__ == "__main__":
    main()
