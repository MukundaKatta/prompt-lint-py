# prompt-lint-py

Static lint rules for LLM prompt quality. Catch common issues — unfilled
template placeholders, prompts that are too long or too short, duplicated
instructions, forbidden words, missing required terms — **before** you send a
prompt to a model.

No runtime dependencies. Pure standard library. Works on Python 3.9+.

## Install

```bash
pip install prompt-lint-py
```

Or from source:

```bash
git clone https://github.com/MukundaKatta/prompt-lint-py
cd prompt-lint-py
pip install -e .
```

## Usage

Build a linter by chaining rule builders, then call `lint()`:

```python
from prompt_lint import PromptLinter

linter = (
    PromptLinter()
    .add_not_empty()
    .add_max_length(max_chars=4000)
    .add_min_length(min_chars=20)
    .add_no_placeholder()                       # flags {unfilled} vars
    .add_no_duplicate_instructions()
    .add_no_forbidden_words(["ignore", "disregard"], severity="error")
    .add_require_word("assistant")              # must appear
)

result = linter.lint("You are a helpful {assistant_type}.")

for issue in result.issues:
    print(f"[{issue.severity}] {issue.rule}: {issue.message}")

if result.ok:           # no errors (warnings are tolerated)
    print(result.summary())
    # send_to_llm(prompt)

if result.passed:       # stricter: no errors AND no warnings
    ...
```

`LintResult` is truthy when it is `ok`, so you can write:

```python
if not linter.lint(prompt):
    raise ValueError("prompt failed linting")
```

## Command line

The package ships a small CLI. It reads a prompt from a file (or `-` for
stdin), prints any issues, and exits non-zero when an `error`-severity issue is
found — handy as a CI or pre-commit gate.

```bash
# Lint a file
prompt-lint prompt.txt

# Lint from stdin, fail on a forbidden term
cat prompt.txt | prompt-lint - --forbidden secret --forbidden internal

# Equivalent without installing the console script
python -m prompt_lint prompt.txt
```

Flags: `--max-chars` (default 8000), `--min-chars` (default 1),
`--forbidden WORD` (repeatable, whole-word match), `--version`.

## API

### `PromptLinter`

| Method | Purpose |
| --- | --- |
| `add(name, rule)` | Register a custom `Callable[[str], list[LintIssue]]`. |
| `add_not_empty(severity="error")` | Flag empty / whitespace-only prompts. |
| `add_max_length(max_chars, severity="warning")` | Flag prompts longer than `max_chars`. |
| `add_min_length(min_chars, severity="warning")` | Flag prompts shorter than `min_chars`. |
| `add_no_placeholder(pattern=r"\{[a-zA-Z_]\w*\}", severity="error")` | Flag unfilled `{template}` placeholders. |
| `add_no_duplicate_instructions(min_similarity=3, severity="warning")` | Flag repeated sentences (word-overlap heuristic). |
| `add_no_forbidden_words(words, severity="error", name="no_forbidden", whole_word=False)` | Flag forbidden terms. Set `whole_word=True` to match on word boundaries. |
| `add_require_word(word, severity="warning")` | Require a term to appear. |
| `add_language_check(severity="info")` | Flag prompts that mix scripts (non-ASCII heuristic). |
| `lint(text)` | Run all rules and return a `LintResult`. |
| `rule_names()` | List registered rule names. |

All `add_*` methods return `self`, so calls can be chained.

### `LintResult`

| Member | Meaning |
| --- | --- |
| `issues` | All `LintIssue`s produced. |
| `errors` / `warnings` / `infos` | Issues filtered by severity. |
| `ok` | `True` when there are no `error`-severity issues (warnings tolerated). |
| `passed` | `True` only when there are no errors **and** no warnings. |
| `summary()` | One-line counts, e.g. `"1 error(s), 0 warning(s), 0 info(s)"`. |
| `bool(result)` | Same as `result.ok`. |

### `LintIssue`

A dataclass with `rule`, `severity` (`"error" | "warning" | "info"`),
`message`, and optional `line`.

### Custom rules

A rule is any callable that takes the prompt text and returns a list of
`LintIssue` (empty when it passes):

```python
from prompt_lint import LintIssue, PromptLinter

def no_exclamation(text: str) -> list[LintIssue]:
    if "!" in text:
        return [LintIssue("no_exclamation", "warning", "Avoid exclamation marks.")]
    return []

linter = PromptLinter().add("no_exclamation", no_exclamation)
```

## Development

Tests use only the standard library — no third-party test runner required:

```bash
python -m unittest discover -s tests
```

## License

MIT
