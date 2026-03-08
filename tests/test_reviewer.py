from llm_code_review.reviewer import ReviewResult, build_messages, parse_response


class TestBuildMessages:
    def test_includes_files_and_diff(self):
        system, user = build_messages("+ added line", ["foo.py", "bar.py"])
        assert "foo.py" in user
        assert "bar.py" in user
        assert "+ added line" in user
        assert "code reviewer" in system.lower()

    def test_empty_files(self):
        system, user = build_messages("some diff", [])
        assert "(unknown)" in user


class TestParseResponse:
    def test_full_format(self):
        raw = (
            "VERDICT: FAIL\n"
            "ISSUES:\n"
            "- [foo.py:10] bug: off-by-one error\n"
            "- [bar.py:5] style: missing docstring\n"
            "SUMMARY: Two issues found\n"
        )
        result = parse_response(raw)
        assert result.verdict == "FAIL"
        assert len(result.issues) == 2
        assert "off-by-one" in result.issues[0]
        assert result.summary == "Two issues found"

    def test_pass_no_issues(self):
        raw = "VERDICT: PASS\nISSUES:\nSUMMARY: Code looks good\n"
        result = parse_response(raw)
        assert result.verdict == "PASS"
        assert result.issues == []
        assert result.summary == "Code looks good"

    def test_garbled_output_defaults_to_warn(self):
        raw = "This is some random text from the LLM that doesn't follow the format."
        result = parse_response(raw)
        assert result.verdict == "WARN"
        assert result.raw == raw
