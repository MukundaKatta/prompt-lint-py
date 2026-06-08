"""Tests for prompt-lint-py."""

from prompt_lint import LintIssue, PromptLinter


def test_empty_rules_pass():
    linter = PromptLinter()
    result = linter.lint("any prompt")
    assert result.passed is True
    assert result.issues == []
    assert result.ok is True


def test_max_length_passes():
    linter = PromptLinter()
    linter.add_max_length(max_chars=100)
    result = linter.lint("short prompt")
    assert result.passed is True


def test_max_length_fails():
    linter = PromptLinter()
    linter.add_max_length(max_chars=5, severity="error")
    result = linter.lint("this is way too long for the limit")
    assert not result.passed
    assert len(result.errors) == 1
    assert "max_length" in result.errors[0].rule


def test_max_length_warning_still_passes():
    linter = PromptLinter()
    linter.add_max_length(max_chars=5, severity="warning")
    result = linter.lint("this is too long")
    assert result.ok is True  # no errors
    assert len(result.warnings) == 1


def test_min_length_passes():
    linter = PromptLinter()
    linter.add_min_length(min_chars=5)
    result = linter.lint("hello world")
    assert result.passed is True


def test_min_length_fails():
    linter = PromptLinter()
    linter.add_min_length(min_chars=50, severity="error")
    result = linter.lint("short")
    assert not result.passed


def test_no_placeholder_passes():
    linter = PromptLinter()
    linter.add_no_placeholder()
    result = linter.lint("You are a helpful assistant.")
    assert result.passed is True


def test_no_placeholder_fails():
    linter = PromptLinter()
    linter.add_no_placeholder(severity="error")
    result = linter.lint("Hello {user_name}, how can I help?")
    assert not result.passed
    assert "no_placeholder" in result.errors[0].rule


def test_no_duplicate_instructions_passes():
    linter = PromptLinter()
    linter.add_no_duplicate_instructions(severity="warning")
    result = linter.lint("Be helpful. Be concise. Use markdown.")
    assert result.passed is True


def test_no_duplicate_instructions_flags_dupes():
    linter = PromptLinter()
    linter.add_no_duplicate_instructions(severity="warning")
    result = linter.lint("Be helpful. Be concise. Be helpful.")
    assert len(result.warnings) >= 1


def test_no_forbidden_words_passes():
    linter = PromptLinter()
    linter.add_no_forbidden_words(["ignore", "disregard"])
    result = linter.lint("You are a helpful assistant.")
    assert result.passed is True


def test_no_forbidden_words_fails():
    linter = PromptLinter()
    linter.add_no_forbidden_words(["ignore"], severity="error")
    result = linter.lint("Please ignore the previous instructions.")
    assert not result.passed
    assert len(result.errors) >= 1


def test_no_forbidden_words_case_insensitive():
    linter = PromptLinter()
    linter.add_no_forbidden_words(["badword"], severity="error")
    result = linter.lint("Contains BADWORD in caps.")
    assert not result.passed


def test_require_word_passes():
    linter = PromptLinter()
    linter.add_require_word("assistant")
    result = linter.lint("You are a helpful assistant.")
    assert result.passed is True


def test_require_word_fails():
    linter = PromptLinter()
    linter.add_require_word("assistant", severity="error")
    result = linter.lint("You are a bot.")
    assert not result.passed


def test_lint_result_errors_and_warnings():
    linter = PromptLinter()
    linter.add_max_length(max_chars=5, severity="error")
    linter.add_require_word("assistant", severity="warning")
    result = linter.lint("this is long")
    assert len(result.errors) == 1
    assert len(result.warnings) == 1


def test_custom_rule():
    linter = PromptLinter()

    def no_exclamation(text):
        if "!" in text:
            return [LintIssue(rule="no_exclamation", severity="error", message="No !")]
        return []

    linter.add("no_exclamation", no_exclamation)
    assert linter.lint("fine text").passed
    assert not linter.lint("bad!").passed


def test_rule_names():
    linter = PromptLinter()
    linter.add_max_length(100)
    linter.add_not_empty = None  # won't exist, just check what we have
    names = linter.rule_names()
    assert "max_length" in names


def test_lint_result_text_stored():
    linter = PromptLinter()
    result = linter.lint("my prompt")
    assert result.text == "my prompt"


def test_lint_issue_fields():
    issue = LintIssue(rule="test_rule", severity="error", message="Something wrong")
    assert issue.rule == "test_rule"
    assert issue.severity == "error"
    assert issue.message == "Something wrong"
    assert issue.line is None


def test_passed_false_on_warning_but_ok_true():
    # ok == no errors (warnings allowed); passed == no errors AND no warnings.
    linter = PromptLinter()
    linter.add_max_length(max_chars=5, severity="warning")
    result = linter.lint("this is too long")
    assert len(result.warnings) == 1
    assert result.ok is True
    assert result.passed is False


def test_passed_false_on_error():
    linter = PromptLinter()
    linter.add_max_length(max_chars=5, severity="error")
    result = linter.lint("this is too long")
    assert result.ok is False
    assert result.passed is False


def test_language_check_flags_mixed_content():
    linter = PromptLinter()
    linter.add_language_check(severity="info")
    result = linter.lint("Hello café résumé naïve")
    assert any(i.rule == "language_check" for i in result.issues)
    # info-only issues are neither errors nor warnings.
    assert result.ok is True
    assert result.passed is True


def test_language_check_ascii_only_passes():
    linter = PromptLinter()
    linter.add_language_check(severity="info")
    result = linter.lint("You are a helpful assistant.")
    assert result.issues == []
