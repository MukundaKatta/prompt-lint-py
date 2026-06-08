"""Command-line interface for prompt-lint-py.

Run a small set of default lint rules against a prompt read from a file or
standard input::

    python -m prompt_lint prompt.txt
    cat prompt.txt | python -m prompt_lint -

The process exits with status 1 when any ``error``-severity issue is found,
making it usable as a CI / pre-commit gate.
"""

from __future__ import annotations

import argparse
import sys

from . import PromptLinter, __version__


def build_default_linter(
    max_chars: int,
    min_chars: int,
    forbidden: list[str],
) -> PromptLinter:
    """Construct a linter with a sensible default rule set."""
    linter = PromptLinter()
    linter.add_not_empty()
    linter.add_max_length(max_chars=max_chars)
    linter.add_min_length(min_chars=min_chars)
    linter.add_no_placeholder()
    linter.add_no_duplicate_instructions()
    if forbidden:
        linter.add_no_forbidden_words(forbidden, whole_word=True)
    return linter


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="prompt-lint",
        description="Static lint rules for LLM prompt quality.",
    )
    parser.add_argument(
        "path",
        help="Path to a prompt file, or '-' to read from stdin.",
    )
    parser.add_argument(
        "--max-chars", type=int, default=8000, help="Maximum prompt length."
    )
    parser.add_argument(
        "--min-chars", type=int, default=1, help="Minimum prompt length."
    )
    parser.add_argument(
        "--forbidden",
        action="append",
        default=[],
        metavar="WORD",
        help="Forbidden word (whole-word match). May be repeated.",
    )
    parser.add_argument(
        "--version", action="version", version=f"prompt-lint-py {__version__}"
    )
    args = parser.parse_args(argv)

    try:
        text = _read_text(args.path)
    except OSError as exc:
        print(f"error: could not read {args.path!r}: {exc}", file=sys.stderr)
        return 2

    linter = build_default_linter(args.max_chars, args.min_chars, args.forbidden)
    result = linter.lint(text)

    for issue in result.issues:
        line = f":{issue.line}" if issue.line is not None else ""
        print(f"[{issue.severity}] {issue.rule}{line}: {issue.message}")

    print(result.summary(), file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
