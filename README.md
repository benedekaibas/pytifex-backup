# Pytifex

**Pytifex** is a research tool that automatically discovers disagreements between Python type checkers. It finds cases where type checkers (mypy, pyrefly, zuban, ty) produce different results on the same code—revealing false positives, false negatives, and implementation differences.

## Core Idea

The key insight is to use **real bugs from type checker repositories** as seeds for generating new test cases:

1. **Fetch closed GitHub issues** from mypy, pyrefly, and ty repositories
2. **Extract code examples** from bug reports (especially false positives/negatives)
3. **Generate variations** using an LLM (Gemini) that might trigger similar bugs
4. **Run all 4 type checkers** and keep only examples where they disagree
5. **Evaluate** which checker is correct using LLM-based analysis

This approach is more effective than asking an LLM to generate examples from scratch, because it's grounded in real, proven type system edge cases.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 0: Fetch seed examples from GitHub                        │
│   - python/mypy, facebook/pyrefly, astral-sh/ty                 │
│   - Extract Python code blocks from closed bug issues           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Generate variations with Gemini                        │
│   - Show 3-5 real bug examples to the LLM                       │
│   - Ask it to create NEW variations targeting similar patterns  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Run type checkers & filter                              │
│   - Run mypy, pyrefly, zuban, ty on each generated example      │
│   - Keep ONLY examples where at least one checker disagrees     │
│   - Discard examples where all checkers agree                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Refine failures (optional)                              │
│   - For non-divergent examples, send back to LLM with feedback  │
│   - "All checkers agreed. Modify to create a divergence."       │
│   - Re-run checkers on refined version                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Evaluate correctness                                    │
│   - Use LLM to analyze which checker is correct                 │
│   - Methods: multi-step analysis, consensus, runtime validation │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/benedekaibas/pytifex-demo.git
cd pytifex-demo/src/tc_disagreement

# Set your Gemini API key (required)
export GEMINI_API_KEY=your_gemini_api_key

# Optional: Set GitHub token for higher rate limits
export GITHUB_TOKEN=ghp_your_github_token
```

The type checkers (mypy, pyrefly, zuban, ty) are automatically installed by `uv` when you run the script.

## Usage

### Basic Usage

```bash
# Run the full pipeline: generate → filter → evaluate
uv run main.py

# Generate until 5 disagreements are found (default)
uv run main.py --num-examples 5

# Use a different Gemini model
uv run main.py --model gemini-2.5-pro
```

### Commands

| Command | Description |
|---------|-------------|
| `uv run main.py` | Run full pipeline (default) |
| `uv run main.py full` | Same as above |
| `uv run main.py generate` | Only generate examples (no evaluation) |
| `uv run main.py check` | Run type checkers on existing examples |
| `uv run main.py eval` | Evaluate existing results |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--num-examples N` | 5 | Target number of disagreement examples to find |
| `--batch-size N` | 15 | Examples to generate per LLM call |
| `--max-attempts N` | 5 | Maximum generation attempts before giving up |
| `--max-refinements N` | 2 | Refinement attempts per non-divergent example |
| `--model MODEL` | gemini-2.5-flash | Gemini model to use |
| `--eval-method METHOD` | all | Evaluation method (multi_step, consensus, runtime, all) |
| `--no-github` | false | Skip fetching seeds from GitHub issues |
| `-v, --verbose` | false | Show all examples, not just disagreements |

### Examples

```bash
# Quick test: find 2 disagreements
uv run main.py --num-examples 2

# Verbose output to see what's happening
uv run main.py --num-examples 3 -v

# Skip GitHub (use pattern-based generation only)
uv run main.py --no-github

# Use the more capable model
uv run main.py --model gemini-2.5-pro --num-examples 10

# Disable refinement (faster but lower hit rate)
uv run main.py --max-refinements 0

# Only run evaluation on existing results
uv run main.py eval --eval-method consensus
```

## Output Structure

Each run creates a timestamped folder:

```
generated_examples/
└── 2026-01-13_21-30-00/
    ├── source_files/                    # Python files with disagreements
    │   ├── protocol-defaults-1.py
    │   ├── typeguard-narrowing-2.py
    │   └── typed-dict-total-3.py
    ├── results.json                     # Type checker outputs
    └── evaluation_all.json              # LLM correctness analysis
```

### results.json

Contains the raw output from each type checker:

```json
{
  "timestamp": "2026-01-13T21:30:00",
  "model_used": "gemini-2.5-flash",
  "total_generated": 45,
  "disagreements_found": 5,
  "success_rate": "11.1%",
  "checkers_used": ["mypy", "pyrefly", "zuban", "ty"],
  "results": [
    {
      "filename": "protocol-defaults-1.py",
      "filepath": "generated_examples/.../source_files/protocol-defaults-1.py",
      "outputs": {
        "mypy": "Success: no issues found",
        "pyrefly": "error: Incompatible types...",
        "zuban": "Success: no issues found",
        "ty": "error[invalid-argument-type]: ..."
      },
      "statuses": {
        "mypy": "ok",
        "pyrefly": "error",
        "zuban": "ok",
        "ty": "error"
      }
    }
  ]
}
```

### evaluation_all.json

Contains the LLM's analysis of which checker is correct:

```json
{
  "method": "all",
  "evaluations": [
    {
      "filename": "protocol-defaults-1.py",
      "evaluations": {
        "mypy": [
          {
            "verdict": "INCORRECT",
            "reason": "Failed to detect the protocol violation",
            "method": "multi_step"
          }
        ],
        "pyrefly": [
          {
            "verdict": "CORRECT",
            "reason": "Correctly identified the incompatible types",
            "method": "multi_step"
          }
        ]
      }
    }
  ]
}
```

## Type Checker Targets

Pytifex tests these four type checkers:

| Checker | Version | Command |
|---------|---------|---------|
| [mypy](https://github.com/python/mypy) | 1.19.0 | `mypy file.py` |
| [pyrefly](https://github.com/facebook/pyrefly) | 0.44.2 | `pyrefly check file.py` |
| [zuban](https://pypi.org/project/zuban/) | 0.3.0 | `zuban check file.py` |
| [ty](https://github.com/astral-sh/ty) | 0.0.1-alpha.32 | `ty check file.py` |

## Divergence Patterns

The tool targets these known areas of type checker disagreement:

| Pattern | Description | PEP References |
|---------|-------------|----------------|
| protocol-defaults | Protocol methods with different default argument values | PEP 544 |
| typed-dict-total | TypedDict with mixed total/Required/NotRequired inheritance | PEP 589, 655 |
| typeguard-narrowing | TypeGuard/TypeIs with generic type parameters | PEP 647, 742 |
| param-spec-decorator | ParamSpec decorators on classmethods/staticmethods | PEP 612 |
| self-generic | Self type in generic classes with abstract methods | PEP 673 |
| newtype-containers | NewType in containers (covariance/contravariance) | PEP 484 |
| overload-literals | Overloaded functions with Literal type discrimination | PEP 484, 586 |
| final-override | Final attributes overridden by properties | PEP 591 |
| keyword-vs-positional | Protocol callables with keyword-only parameters | PEP 544, 570 |
| bounded-typevars | TypeVar bounds with nested generics | PEP 484 |

## Evaluation Methods

The tool uses three methods to evaluate type checker correctness:

### 1. Multi-Step Analysis (`multi_step`)

1. LLM independently analyzes the code for type issues
2. LLM compares each checker's output against its analysis
3. Determines if the checker caught real issues or produced false positives/negatives

### 2. Consensus Analysis (`consensus`)

1. Collects outputs from all 4 checkers
2. Identifies what the majority agrees on
3. Analyzes whether the minority or majority is likely correct

### 3. Runtime Validation (`runtime`)

1. Analyzes if the code would cause runtime errors
2. Checks if type checkers should have caught those errors
3. Validates that reported errors correspond to real issues

## Architecture

```
src/tc_disagreement/
├── main.py              # CLI entry point
├── pipeline.py          # Core generation/filtering pipeline
├── github_issues.py     # Fetches code examples from GitHub issues
├── prompts.py           # LLM prompt builders
├── patterns.py          # Known divergence pattern definitions
├── agent.py             # Gemini API client
├── run_checkers.py      # Type checker execution
├── eval.py              # Correctness evaluation
├── generate_json.py     # Parsing LLM output
└── config.py            # Shared constants
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for code generation |
| `GITHUB_TOKEN` | No | GitHub token for higher API rate limits (60→5000 req/hr) |

## Troubleshooting

### "No disagreements found"

- Increase `--max-attempts` or `--batch-size`
- Try `--model gemini-2.5-pro` for better examples
- Enable refinement: `--max-refinements 3`

### GitHub rate limit errors

- Set `GITHUB_TOKEN` environment variable
- Or use `--no-github` to skip GitHub fetching

### Type checker not found

- Ensure you're running with `uv run` (auto-installs dependencies)
- Or manually install: `pip install mypy pyrefly zuban ty`

## Contributing

Contributions welcome! Areas for improvement:

- Add more divergence patterns to `patterns.py`
- Improve GitHub issue parsing in `github_issues.py`
- Add support for more type checkers (pyright, pyre)
- Create a web UI for browsing results

## License

MIT License
