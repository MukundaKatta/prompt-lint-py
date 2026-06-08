"""prompt-lint-py — static lint rules for prompt quality."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

__version__ = "0.1.0"


@dataclass
class LintIssue:
    """A single lint finding."""

    rule: str
    severity: str  # "error" | "warning" | "info"
    message: str
    line: int | None = None


@dataclass
class LintResult:
    """Result of linting a prompt."""

    issues: list[LintIssue]
    passed: bool
    text: str

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def infos(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "info"]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def __bool__(self) -> bool:
        """A result is truthy when it is ``ok`` (no errors)."""
        return self.ok

    def summary(self) -> str:
        """Return a one-line, human-readable summary of the result."""
        return (
            f"{len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s), "
            f"{len(self.infos)} info(s)"
        )


class PromptLinter:
    """
    Static lint rules for LLM system prompts.

    Add built-in rules or custom rules. Run with .lint().

    Example::

        linter = PromptLinter()
        linter.add_max_length(max_chars=4000)
        linter.add_no_placeholder()
        linter.add_no_duplicate_instructions()
        linter.add_language_check()

        result = linter.lint("You are a helpful assistant. Be helpful.")
        for issue in result.issues:
            print(f"[{issue.severity}] {issue.rule}: {issue.message}")
    """

    def __init__(self) -> None:
        self._rules: list[tuple[str, Callable[[str], list[LintIssue]]]] = []

    def add(self, name: str, rule: Callable[[str], list[LintIssue]]) -> "PromptLinter":
        """Add a custom lint rule function."""
        self._rules.append((name, rule))
        return self

    def add_max_length(
        self, max_chars: int, severity: str = "warning"
    ) -> "PromptLinter":
        """Warn/error if the prompt exceeds max_chars."""

        def rule(text: str) -> list[LintIssue]:
            if len(text) > max_chars:
                return [
                    LintIssue(
                        rule="max_length",
                        severity=severity,
                        message=f"Prompt is {len(text)} chars, exceeds max {max_chars}.",
                    )
                ]
            return []

        return self.add("max_length", rule)

    def add_min_length(
        self, min_chars: int, severity: str = "warning"
    ) -> "PromptLinter":
        """Warn/error if the prompt is shorter than min_chars."""

        def rule(text: str) -> list[LintIssue]:
            if len(text) < min_chars:
                return [
                    LintIssue(
                        rule="min_length",
                        severity=severity,
                        message=f"Prompt is only {len(text)} chars, minimum is {min_chars}.",
                    )
                ]
            return []

        return self.add("min_length", rule)

    def add_no_placeholder(
        self, pattern: str = r"\{[a-zA-Z_]\w*\}", severity: str = "error"
    ) -> "PromptLinter":
        """Flag unfilled template placeholders like {variable_name}."""
        compiled = re.compile(pattern)

        def rule(text: str) -> list[LintIssue]:
            found = compiled.findall(text)
            if found:
                return [
                    LintIssue(
                        rule="no_placeholder",
                        severity=severity,
                        message=f"Unfilled placeholder(s) found: {found}",
                    )
                ]
            return []

        return self.add("no_placeholder", rule)

    def add_no_duplicate_instructions(
        self, min_similarity: int = 3, severity: str = "warning"
    ) -> "PromptLinter":
        """Flag repeated sentences or clauses (naive word-overlap heuristic)."""

        def rule(text: str) -> list[LintIssue]:
            sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
            seen: set[str] = set()
            dupes: list[str] = []
            for s in sentences:
                normalized = " ".join(sorted(s.lower().split()))
                if normalized in seen:
                    dupes.append(s[:60])
                else:
                    seen.add(normalized)
            if dupes:
                return [
                    LintIssue(
                        rule="no_duplicate_instructions",
                        severity=severity,
                        message=f"Possible duplicate instruction(s): {dupes}",
                    )
                ]
            return []

        return self.add("no_duplicate_instructions", rule)

    def add_no_forbidden_words(
        self,
        words: list[str],
        severity: str = "error",
        name: str = "no_forbidden",
        whole_word: bool = False,
    ) -> "PromptLinter":
        """Flag prompts containing forbidden words.

        Matching is case-insensitive. By default a forbidden term is matched as
        a substring (``"ignore"`` also matches inside ``"ignored"``). Pass
        ``whole_word=True`` to match only on word boundaries, which avoids
        false positives such as ``"ass"`` matching inside ``"assistant"``.
        """
        lwords = [w.lower() for w in words]

        if whole_word:
            patterns = [
                (w, re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE))
                for w in lwords
            ]

            def rule(text: str) -> list[LintIssue]:
                found = [w for w, pat in patterns if pat.search(text)]
                if found:
                    return [
                        LintIssue(
                            rule=name,
                            severity=severity,
                            message=f"Forbidden word(s) found: {found}",
                        )
                    ]
                return []

        else:

            def rule(text: str) -> list[LintIssue]:
                text_lower = text.lower()
                found = [w for w in lwords if w in text_lower]
                if found:
                    return [
                        LintIssue(
                            rule=name,
                            severity=severity,
                            message=f"Forbidden word(s) found: {found}",
                        )
                    ]
                return []

        return self.add(name, rule)

    def add_language_check(self, severity: str = "info") -> "PromptLinter":
        """Flag prompts that appear to mix multiple languages (simple heuristic)."""

        # Heuristic: detect non-ASCII characters at >10% of content
        def rule(text: str) -> list[LintIssue]:
            if not text:
                return []
            non_ascii = sum(1 for c in text if ord(c) > 127)
            ratio = non_ascii / len(text)
            if 0 < ratio < 0.8:  # mixed content
                return [
                    LintIssue(
                        rule="language_check",
                        severity=severity,
                        message=f"Prompt appears to mix languages ({ratio:.0%} non-ASCII).",
                    )
                ]
            return []

        return self.add("language_check", rule)

    def add_not_empty(self, severity: str = "error") -> "PromptLinter":
        """Flag prompts that are empty or contain only whitespace."""

        def rule(text: str) -> list[LintIssue]:
            if not text.strip():
                return [
                    LintIssue(
                        rule="not_empty",
                        severity=severity,
                        message="Prompt is empty or whitespace-only.",
                    )
                ]
            return []

        return self.add("not_empty", rule)

    def add_require_word(self, word: str, severity: str = "warning") -> "PromptLinter":
        """Require a specific word or phrase to appear in the prompt."""

        def rule(text: str) -> list[LintIssue]:
            if word.lower() not in text.lower():
                return [
                    LintIssue(
                        rule=f"require_word:{word}",
                        severity=severity,
                        message=f"Required word '{word}' not found in prompt.",
                    )
                ]
            return []

        return self.add(f"require_word:{word}", rule)

    def lint(self, text: str) -> LintResult:
        """Run all rules against *text* and return a LintResult."""
        all_issues: list[LintIssue] = []
        for _, rule in self._rules:
            all_issues.extend(rule(text))
        # passed == no errors AND no warnings; ok (on LintResult) == no errors only.
        passed = all(i.severity not in ("error", "warning") for i in all_issues)
        return LintResult(issues=all_issues, passed=passed, text=text)

    def rule_names(self) -> list[str]:
        return [name for name, _ in self._rules]


__all__ = ["PromptLinter", "LintIssue", "LintResult", "__version__"]
