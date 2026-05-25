# prompt-lint-py

Static lint rules for LLM prompt quality. Catch common issues before sending prompts to a model.

## Install

```bash
pip install prompt-lint-py
```

## Usage

```python
from prompt_lint import PromptLinter

linter = PromptLinter()
linter.add_max_length(max_chars=4000)
linter.add_min_length(min_chars=20)
linter.add_no_placeholder()                    # flags {unfilled} vars
linter.add_no_duplicate_instructions()
linter.add_no_forbidden_words(["ignore", "disregard"], severity="error")
linter.add_require_word("assistant")           # must appear

result = linter.lint("You are a helpful {assistant_type}.")
for issue in result.issues:
    print(f"[{issue.severity}] {issue.rule}: {issue.message}")

if result.ok:           # no errors (warnings OK)
    send_to_llm(prompt)
if result.passed:       # no errors AND no warnings
    ...
```

## License

MIT
