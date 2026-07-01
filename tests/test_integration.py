"""End-to-end integration tests for the skillsaw-typos plugin.

Each test invokes the CLI via subprocess — ``skillsaw lint``,
``skillsaw fix``, and ``skillsaw typos accept`` — against realistic
fixtures and asserts on the parsed output, file contents, and exit codes.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixture"


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE, repo)
    return repo


def run_lint(path, *extra_args, fmt="json"):
    args = [sys.executable, "-m", "skillsaw", "lint"]
    if fmt:
        args.extend(["--format", fmt])
    args.append(str(path))
    args.extend(extra_args)
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    output = None
    if fmt == "json" and result.stdout.strip():
        output = json.loads(result.stdout)
    return {
        "rc": result.returncode,
        "out": output,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_fix(path, *extra_args):
    args = [sys.executable, "-m", "skillsaw", "fix"]
    args.extend(extra_args)
    args.append(str(path))
    return subprocess.run(args, capture_output=True, text=True, timeout=60)


def run_accept(path):
    return subprocess.run(
        [sys.executable, "-m", "skillsaw_typos.cli", "accept", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )


# ── Plugin loading ──────────────────────────────────────────────


class TestPluginLoading:
    def test_plugin_appears_in_plugins_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "skillsaw", "plugins"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "typos" in result.stdout
        assert "typo" in result.stdout

    def test_explain_shows_rule_config(self):
        result = subprocess.run(
            [sys.executable, "-m", "skillsaw", "explain", "typo"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ignore-words" in result.stdout
        assert "extra-dictionaries" in result.stdout

    def test_no_plugins_flag_hides_rule(self, tmp_path):
        repo = make_repo(tmp_path)
        r = run_lint(repo, "--no-plugins")
        typo_violations = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        assert typo_violations == []


# ── Lint ────────────────────────────────────────────────────────


class TestLint:
    def test_detects_misspellings_with_correct_metadata(self, tmp_path):
        repo = make_repo(tmp_path)
        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]

        assert len(typos) == 3
        words = {v["message"].split("'")[1] for v in typos}
        assert words == {"seperate", "recieve", "occured"}

        for v in typos:
            assert v["source"] == "plugin:typos"
            assert v["severity"] == "warning"
            assert v["line"] is not None

    def test_code_block_typos_not_flagged(self, tmp_path):
        repo = make_repo(tmp_path)
        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        all_messages = " ".join(v["message"] for v in typos)
        assert "teh" not in all_messages

    def test_clean_repo_passes(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "CLAUDE.md").write_text(
            "# Standards\n\nAll code must be reviewed before merging.\n",
            encoding="utf-8",
        )
        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        assert typos == []

    def test_ignore_file_suppresses_violations(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / ".skillsaw-typos-ignore").write_text(
            "seperate\nrecieve\noccured\n",
            encoding="utf-8",
        )
        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        assert typos == []


# ── Fix ─────────────────────────────────────────────────────────


class TestFix:
    def test_fix_corrects_misspellings(self, tmp_path):
        repo = make_repo(tmp_path)
        claude_md = repo / "CLAUDE.md"
        original = claude_md.read_text(encoding="utf-8")

        result = run_fix(repo, "--rule", "typo")
        assert result.returncode == 0
        assert "Fixed" in result.stdout

        fixed = claude_md.read_text(encoding="utf-8")
        assert "seperate" not in fixed
        assert "separate" in fixed
        assert "recieve" not in fixed
        assert "receive" in fixed
        assert "occured" not in fixed
        assert "occurred" in fixed
        # Code block content untouched
        assert "teh" in fixed
        # Line count preserved
        assert len(fixed.splitlines()) == len(original.splitlines())

    def test_fix_then_lint_clean(self, tmp_path):
        repo = make_repo(tmp_path)
        run_fix(repo, "--rule", "typo")

        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        assert typos == []

    def test_fix_idempotent(self, tmp_path):
        repo = make_repo(tmp_path)
        run_fix(repo, "--rule", "typo")
        after_first = (repo / "CLAUDE.md").read_text(encoding="utf-8")

        result = run_fix(repo, "--rule", "typo")
        after_second = (repo / "CLAUDE.md").read_text(encoding="utf-8")
        assert after_first == after_second
        assert "No auto-fixable" in result.stdout

    def test_dry_run_does_not_modify(self, tmp_path):
        repo = make_repo(tmp_path)
        original = (repo / "CLAUDE.md").read_text(encoding="utf-8")

        result = run_fix(repo, "--rule", "typo", "--dry-run")
        assert result.returncode == 0
        assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == original


# ── Accept ──────────────────────────────────────────────────────


class TestAccept:
    def test_accept_creates_ignore_file(self, tmp_path):
        repo = make_repo(tmp_path)
        result = run_accept(repo)
        assert result.returncode == 0

        ignore_path = repo / ".skillsaw-typos-ignore"
        assert ignore_path.exists()
        words = {
            w.strip()
            for w in ignore_path.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.startswith("#")
        }
        assert words == {"seperate", "recieve", "occured"}

    def test_accept_then_lint_clean(self, tmp_path):
        repo = make_repo(tmp_path)
        run_accept(repo)

        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        assert typos == []

    def test_accept_idempotent(self, tmp_path):
        repo = make_repo(tmp_path)
        run_accept(repo)
        result = run_accept(repo)
        assert result.returncode == 0
        assert "nothing to accept" in result.stdout


# ── Full workflow ───────────────────────────────────────────────


class TestFullWorkflow:
    """Exercise the realistic adoption workflow: lint → fix real typos → accept jargon → clean."""

    def test_lint_fix_accept_cycle(self, tmp_path):
        """Realistic adoption: lint → fix real typos → accept jargon → clean."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "CLAUDE.md").write_text(
            "# Standards\n\n"
            "All handlers should recieve validated input.\n"
            "Use the SME review process for approvals.\n"
            "Check for regressions before merging.\n",
            encoding="utf-8",
        )

        # 1. Lint: both "recieve" and "sme" are flagged
        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        flagged_words = {v["message"].split("'")[1].lower() for v in typos}
        assert "recieve" in flagged_words
        assert "sme" in flagged_words

        # 2. Accept the jargon first so only the real typo remains
        ignore_path = repo / ".skillsaw-typos-ignore"
        ignore_path.write_text("sme\n", encoding="utf-8")

        # 3. Fix the real typo (now the only violation is single-correction → SAFE)
        run_fix(repo, "--rule", "typo")
        fixed = (repo / "CLAUDE.md").read_text(encoding="utf-8")
        assert "receive" in fixed
        assert "recieve" not in fixed
        # Jargon untouched
        assert "SME" in fixed

        # 4. Re-lint: clean
        r = run_lint(repo)
        typos = [v for v in r["out"]["violations"] if v["rule_id"] == "typo"]
        assert typos == []
