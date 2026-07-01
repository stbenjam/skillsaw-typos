"""Tests for the skillsaw-typos plugin."""

import shutil
from pathlib import Path

from skillsaw.context import RepositoryContext
from skillsaw.rules.builtin.utils import invalidate_read_caches

from skillsaw_typos import SKILLSAW_RULES
from skillsaw_typos.rules import TypoRule

FIXTURE = Path(__file__).parent / "fixture"


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE, repo)
    return repo


def test_rule_is_exported():
    assert TypoRule in SKILLSAW_RULES


def test_flags_misspellings(tmp_path):
    context = RepositoryContext(make_repo(tmp_path))
    violations = TypoRule().check(context)
    words = [v.message.split("'")[1] for v in violations]
    assert "seperate" in words
    assert "recieve" in words
    assert "occured" in words
    assert len(violations) == 3


def test_code_block_not_flagged(tmp_path):
    """'teh' inside a code fence must not be flagged."""
    context = RepositoryContext(make_repo(tmp_path))
    violations = TypoRule().check(context)
    messages = " ".join(v.message for v in violations)
    assert "teh" not in messages


def test_clean_content_no_violations(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "CLAUDE.md").write_text(
        "# Standards\n\nAll code must be reviewed before merging.\n",
        encoding="utf-8",
    )
    context = RepositoryContext(repo)
    assert TypoRule().check(context) == []


def test_ignore_words(tmp_path):
    context = RepositoryContext(make_repo(tmp_path))
    rule = TypoRule({"ignore-words": ["seperate", "recieve", "occured"]})
    assert rule.check(context) == []


def test_extra_dictionaries(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "CLAUDE.md").write_text(
        "# Standards\n\nUse the frobnicator for all builds.\n",
        encoding="utf-8",
    )
    extra = tmp_path / "extra.txt"
    extra.write_text("frobnicator->frobnifier\n", encoding="utf-8")
    context = RepositoryContext(repo)
    rule = TypoRule({"extra-dictionaries": [str(extra)]})
    violations = rule.check(context)
    assert len(violations) == 1
    assert "frobnicator" in violations[0].message


def test_autofix_replaces_flagged_words(tmp_path):
    repo = make_repo(tmp_path)
    claude_md = repo / "CLAUDE.md"
    original = claude_md.read_text(encoding="utf-8")
    original_line_count = len(original.splitlines())

    context = RepositoryContext(repo)
    rule = TypoRule()
    violations = rule.check(context)
    fixes = rule.fix(context, violations)
    assert len(fixes) == 1

    claude_md.write_text(fixes[0].fixed_content, encoding="utf-8")
    fixed = claude_md.read_text(encoding="utf-8")

    assert "seperate" not in fixed
    assert "separate" in fixed
    assert "recieve" not in fixed
    assert "receive" in fixed
    assert "occured" not in fixed
    assert "occurred" in fixed
    # Code block typo untouched
    assert "teh" in fixed
    # Line count preserved
    assert len(fixed.splitlines()) == original_line_count


def test_autofix_idempotent(tmp_path):
    repo = make_repo(tmp_path)
    claude_md = repo / "CLAUDE.md"

    context = RepositoryContext(repo)
    rule = TypoRule()
    violations = rule.check(context)
    fixes = rule.fix(context, violations)
    claude_md.write_text(fixes[0].fixed_content, encoding="utf-8")

    invalidate_read_caches()
    context = RepositoryContext(repo)
    assert rule.check(context) == []

    # Second fix is a no-op
    fixes2 = rule.fix(context, [])
    assert fixes2 == []


def test_autofix_preserves_case(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "CLAUDE.md").write_text(
        "# Standards\n\nRecieve all input via the API.\n",
        encoding="utf-8",
    )
    context = RepositoryContext(repo)
    rule = TypoRule()
    violations = rule.check(context)
    fixes = rule.fix(context, violations)
    assert "Receive" in fixes[0].fixed_content
