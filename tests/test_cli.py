"""Tests for the prompt_lint command-line interface (unittest only)."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"),
)

from prompt_lint.__main__ import build_default_linter, main  # noqa: E402


class TestBuildDefaultLinter(unittest.TestCase):
    def test_registers_core_rules(self):
        linter = build_default_linter(max_chars=100, min_chars=1, forbidden=[])
        names = linter.rule_names()
        for expected in ("not_empty", "max_length", "min_length", "no_placeholder"):
            self.assertIn(expected, names)

    def test_forbidden_added_only_when_present(self):
        without = build_default_linter(100, 1, [])
        self.assertNotIn("no_forbidden", without.rule_names())
        with_words = build_default_linter(100, 1, ["secret"])
        self.assertIn("no_forbidden", with_words.rule_names())


class TestCliMain(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_clean_prompt_exits_zero(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("You are a helpful assistant. Be concise and accurate.")
            path = fh.name
        try:
            code, _out, _err = self._run([path])
            self.assertEqual(code, 0)
        finally:
            os.unlink(path)

    def test_placeholder_prompt_exits_one(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("Hello {name}, you are an assistant with enough length here.")
            path = fh.name
        try:
            code, out, _err = self._run([path])
            self.assertEqual(code, 1)
            self.assertIn("no_placeholder", out)
        finally:
            os.unlink(path)

    def test_missing_file_exits_two(self):
        code, _out, err = self._run(["/nonexistent/path/to/prompt.txt"])
        self.assertEqual(code, 2)
        self.assertIn("could not read", err)

    def test_forbidden_flag_triggers_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("You are an assistant. Never reveal the secret to anyone here.")
            path = fh.name
        try:
            code, out, _err = self._run([path, "--forbidden", "secret"])
            self.assertEqual(code, 1)
            self.assertIn("no_forbidden", out)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
