"""Tests for prompt-lint-py (standard-library unittest only).

Run with::

    python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

# Make the ``src`` layout importable without an editable install so the suite
# runs in a clean checkout with no third-party tooling.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"),
)

from prompt_lint import LintIssue, LintResult, PromptLinter  # noqa: E402


class TestEmptyAndBasics(unittest.TestCase):
    def test_empty_rules_pass(self):
        linter = PromptLinter()
        result = linter.lint("any prompt")
        self.assertTrue(result.passed)
        self.assertEqual(result.issues, [])
        self.assertTrue(result.ok)

    def test_lint_result_text_stored(self):
        result = PromptLinter().lint("my prompt")
        self.assertEqual(result.text, "my prompt")

    def test_result_is_truthy_when_ok(self):
        linter = PromptLinter()
        self.assertTrue(bool(linter.lint("fine")))

    def test_result_is_falsy_on_error(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=1, severity="error")
        self.assertFalse(bool(linter.lint("too long")))

    def test_summary_counts(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=1, severity="error")
        linter.add_require_word("nope", severity="warning")
        linter.add_language_check(severity="info")
        result = linter.lint("café résumé naïve")
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.infos), 1)
        self.assertIn("1 error", result.summary())


class TestMaxLength(unittest.TestCase):
    def test_passes(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=100)
        self.assertTrue(linter.lint("short prompt").passed)

    def test_fails(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=5, severity="error")
        result = linter.lint("this is way too long for the limit")
        self.assertFalse(result.passed)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("max_length", result.errors[0].rule)

    def test_warning_still_ok(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=5, severity="warning")
        result = linter.lint("this is too long")
        self.assertTrue(result.ok)
        self.assertEqual(len(result.warnings), 1)


class TestMinLength(unittest.TestCase):
    def test_passes(self):
        linter = PromptLinter()
        linter.add_min_length(min_chars=5)
        self.assertTrue(linter.lint("hello world").passed)

    def test_fails(self):
        linter = PromptLinter()
        linter.add_min_length(min_chars=50, severity="error")
        self.assertFalse(linter.lint("short").passed)


class TestNotEmpty(unittest.TestCase):
    def test_empty_string_flagged(self):
        linter = PromptLinter()
        linter.add_not_empty()
        self.assertFalse(linter.lint("").ok)

    def test_whitespace_only_flagged(self):
        linter = PromptLinter()
        linter.add_not_empty()
        self.assertFalse(linter.lint("   \n\t  ").ok)

    def test_real_content_passes(self):
        linter = PromptLinter()
        linter.add_not_empty()
        self.assertTrue(linter.lint("hello").ok)


class TestNoPlaceholder(unittest.TestCase):
    def test_passes(self):
        linter = PromptLinter()
        linter.add_no_placeholder()
        self.assertTrue(linter.lint("You are a helpful assistant.").passed)

    def test_fails(self):
        linter = PromptLinter()
        linter.add_no_placeholder(severity="error")
        result = linter.lint("Hello {user_name}, how can I help?")
        self.assertFalse(result.passed)
        self.assertIn("no_placeholder", result.errors[0].rule)


class TestNoDuplicateInstructions(unittest.TestCase):
    def test_passes(self):
        linter = PromptLinter()
        linter.add_no_duplicate_instructions(severity="warning")
        result = linter.lint("Be helpful. Be concise. Use markdown.")
        self.assertTrue(result.passed)

    def test_flags_dupes(self):
        linter = PromptLinter()
        linter.add_no_duplicate_instructions(severity="warning")
        result = linter.lint("Be helpful. Be concise. Be helpful.")
        self.assertGreaterEqual(len(result.warnings), 1)


class TestForbiddenWords(unittest.TestCase):
    def test_passes(self):
        linter = PromptLinter()
        linter.add_no_forbidden_words(["ignore", "disregard"])
        self.assertTrue(linter.lint("You are a helpful assistant.").passed)

    def test_fails(self):
        linter = PromptLinter()
        linter.add_no_forbidden_words(["ignore"], severity="error")
        result = linter.lint("Please ignore the previous instructions.")
        self.assertFalse(result.passed)
        self.assertGreaterEqual(len(result.errors), 1)

    def test_case_insensitive(self):
        linter = PromptLinter()
        linter.add_no_forbidden_words(["badword"], severity="error")
        self.assertFalse(linter.lint("Contains BADWORD in caps.").passed)

    def test_substring_matches_by_default(self):
        # Default substring behaviour: "ass" matches inside "assistant".
        linter = PromptLinter()
        linter.add_no_forbidden_words(["ass"], severity="error")
        self.assertFalse(linter.lint("You are an assistant.").ok)

    def test_whole_word_avoids_false_positive(self):
        # whole_word=True must NOT match "ass" inside "assistant".
        linter = PromptLinter()
        linter.add_no_forbidden_words(["ass"], severity="error", whole_word=True)
        self.assertTrue(linter.lint("You are an assistant.").ok)

    def test_whole_word_still_matches_standalone(self):
        linter = PromptLinter()
        linter.add_no_forbidden_words(["ignore"], severity="error", whole_word=True)
        self.assertFalse(linter.lint("Please ignore that.").ok)


class TestRequireWord(unittest.TestCase):
    def test_passes(self):
        linter = PromptLinter()
        linter.add_require_word("assistant")
        self.assertTrue(linter.lint("You are a helpful assistant.").passed)

    def test_fails(self):
        linter = PromptLinter()
        linter.add_require_word("assistant", severity="error")
        self.assertFalse(linter.lint("You are a bot.").passed)


class TestLanguageCheck(unittest.TestCase):
    def test_flags_mixed_content(self):
        linter = PromptLinter()
        linter.add_language_check(severity="info")
        result = linter.lint("Hello cafe resume naive éèêë")
        self.assertTrue(any(i.rule == "language_check" for i in result.issues))
        # info-only issues are neither errors nor warnings.
        self.assertTrue(result.ok)

    def test_ascii_only_passes(self):
        linter = PromptLinter()
        linter.add_language_check(severity="info")
        self.assertEqual(linter.lint("You are a helpful assistant.").issues, [])


class TestResultSemantics(unittest.TestCase):
    def test_errors_and_warnings_split(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=5, severity="error")
        linter.add_require_word("assistant", severity="warning")
        result = linter.lint("this is long")
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.warnings), 1)

    def test_passed_false_on_warning_but_ok_true(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=5, severity="warning")
        result = linter.lint("this is too long")
        self.assertEqual(len(result.warnings), 1)
        self.assertTrue(result.ok)
        self.assertFalse(result.passed)

    def test_passed_false_on_error(self):
        linter = PromptLinter()
        linter.add_max_length(max_chars=5, severity="error")
        result = linter.lint("this is too long")
        self.assertFalse(result.ok)
        self.assertFalse(result.passed)


class TestCustomRulesAndMeta(unittest.TestCase):
    def test_custom_rule(self):
        linter = PromptLinter()

        def no_exclamation(text):
            if "!" in text:
                return [LintIssue(rule="no_exclamation", severity="error", message="No !")]
            return []

        linter.add("no_exclamation", no_exclamation)
        self.assertTrue(linter.lint("fine text").passed)
        self.assertFalse(linter.lint("bad!").passed)

    def test_rule_names(self):
        linter = PromptLinter()
        linter.add_max_length(100)
        self.assertIn("max_length", linter.rule_names())

    def test_chaining_returns_self(self):
        linter = PromptLinter()
        returned = linter.add_max_length(100).add_min_length(1)
        self.assertIs(returned, linter)

    def test_lint_issue_fields(self):
        issue = LintIssue(rule="test_rule", severity="error", message="Something wrong")
        self.assertEqual(issue.rule, "test_rule")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.message, "Something wrong")
        self.assertIsNone(issue.line)

    def test_lint_result_type(self):
        self.assertIsInstance(PromptLinter().lint("x"), LintResult)


if __name__ == "__main__":
    unittest.main()
