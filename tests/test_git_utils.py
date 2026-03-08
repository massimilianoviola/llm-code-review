import subprocess
from unittest.mock import patch

import pytest

from llm_code_review.git_utils import GitError, get_staged_diff, get_staged_files


class TestGetStagedDiff:
    @patch("llm_code_review.git_utils.subprocess.run")
    def test_returns_diff(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="diff --git a/foo.py\n+hello\n", stderr=""
        )
        result = get_staged_diff()
        assert "diff --git" in result
        assert "+hello" in result

    @patch("llm_code_review.git_utils.subprocess.run")
    def test_empty_diff(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        assert get_staged_diff() == ""

    @patch("llm_code_review.git_utils.subprocess.run", side_effect=FileNotFoundError)
    def test_git_not_found(self, mock_run):
        with pytest.raises(GitError, match="not available"):
            get_staged_diff()


class TestGetStagedFiles:
    @patch("llm_code_review.git_utils.subprocess.run")
    def test_returns_file_list(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="foo.py\nbar.py\n", stderr=""
        )
        files = get_staged_files()
        assert files == ["foo.py", "bar.py"]

    @patch("llm_code_review.git_utils.subprocess.run")
    def test_empty_result(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        assert get_staged_files() == []
