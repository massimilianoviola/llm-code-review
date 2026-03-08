from unittest.mock import patch

from llm_code_review.formatting import prompt_continue
from llm_code_review.reviewer import ReviewResult


class TestPromptContinue:
    @patch("llm_code_review.formatting.sys.stdin")
    def test_non_tty_returns_true(self, mock_stdin):
        mock_stdin.isatty.return_value = False
        assert prompt_continue() is True

    @patch("builtins.input", return_value="y")
    @patch("llm_code_review.formatting.sys.stdin")
    def test_yes_returns_true(self, mock_stdin, mock_input):
        mock_stdin.isatty.return_value = True
        assert prompt_continue() is True

    @patch("builtins.input", return_value="n")
    @patch("llm_code_review.formatting.sys.stdin")
    def test_no_returns_false(self, mock_stdin, mock_input):
        mock_stdin.isatty.return_value = True
        assert prompt_continue() is False

    @patch("builtins.input", return_value="")
    @patch("llm_code_review.formatting.sys.stdin")
    def test_empty_returns_false(self, mock_stdin, mock_input):
        mock_stdin.isatty.return_value = True
        assert prompt_continue() is False
