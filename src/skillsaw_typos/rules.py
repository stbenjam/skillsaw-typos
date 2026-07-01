"""Typo-checking rule using the codespell known-typo dictionary."""

import importlib.resources
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from skillsaw import (
    AutofixConfidence,
    AutofixResult,
    RepositoryContext,
    Rule,
    RuleViolation,
    Severity,
)
from skillsaw.blocks import ContentBlock

_WORD_RE = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)*")


@lru_cache(maxsize=1)
def _load_codespell_dict() -> Dict[str, List[str]]:
    """Load the codespell known-typo dictionary."""
    ref = importlib.resources.files("codespell_lib") / "data" / "dictionary.txt"
    text = ref.read_text(encoding="utf-8")
    typos: Dict[str, List[str]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "->" not in line:
            continue
        word, corrections = line.split("->", 1)
        word = word.strip().lower()
        parts = [c.strip() for c in corrections.split(",") if c.strip()]
        if parts:
            typos[word] = parts
    return typos


def _extract_misspelling(message: str) -> Optional[str]:
    """Extract the misspelled word from a violation message."""
    m = re.match(r"Misspelling: '([^']+)'", message)
    return m.group(1) if m else None


class TypoRule(Rule):
    """Flag misspellings in instruction prose using the codespell dictionary."""

    autofix_confidence = AutofixConfidence.SAFE

    config_schema = {
        "ignore-words": {
            "type": "list",
            "default": [],
            "description": "Words to accept even if flagged by codespell (e.g. project jargon)",
        },
        "extra-dictionaries": {
            "type": "list",
            "default": [],
            "description": (
                "Paths to additional dictionary files in codespell format (word->correction)"
            ),
        },
    }

    @property
    def rule_id(self) -> str:
        return "typo"

    @property
    def description(self) -> str:
        return "Flag misspellings in instruction prose"

    def default_severity(self) -> Severity:
        return Severity.WARNING

    def _build_dict(self) -> Dict[str, List[str]]:
        typos = dict(_load_codespell_dict())

        for path_str in self.config.get("extra-dictionaries", []):
            path = Path(path_str)
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "->" not in line:
                    continue
                word, corrections = line.split("->", 1)
                parts = [c.strip() for c in corrections.split(",") if c.strip()]
                if parts:
                    typos[word.strip().lower()] = parts

        ignore = {w.lower() for w in self.config.get("ignore-words", [])}
        for w in ignore:
            typos.pop(w, None)

        return typos

    def check(self, context: RepositoryContext) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        typos = self._build_dict()

        for block in context.lint_tree.find(ContentBlock):
            content = block.read_body(strip_code_blocks=True)
            if content is None:
                continue
            for i, line in enumerate(content.splitlines(), start=1):
                for match in _WORD_RE.finditer(line):
                    word = match.group()
                    lower = word.lower()
                    if lower in typos:
                        corrections = typos[lower]
                        arrow = " / ".join(corrections)
                        violations.append(
                            self.violation(
                                f"Misspelling: '{word}' → '{arrow}'",
                                block=block,
                                line=i,
                            )
                        )
        return violations

    def fix(self, context: RepositoryContext, violations: List[RuleViolation]) -> List[AutofixResult]:
        typos = self._build_dict()
        by_file: Dict[Path, List[RuleViolation]] = {}
        for v in violations:
            by_file.setdefault(v.file_path, []).append(v)

        results: List[AutofixResult] = []
        for path, file_violations in by_file.items():
            original = path.read_text(encoding="utf-8")
            lines = original.splitlines(keepends=True)

            by_line: Dict[int, List[RuleViolation]] = {}
            for v in file_violations:
                if v.file_line:
                    by_line.setdefault(v.file_line, []).append(v)

            all_safe = all(
                len(typos.get(_extract_misspelling(v.message).lower(), [])) == 1
                for v in file_violations
                if _extract_misspelling(v.message)
            )

            fixed_lines = list(lines)
            for file_line, line_violations in by_line.items():
                idx = file_line - 1
                if idx < 0 or idx >= len(fixed_lines):
                    continue
                current = fixed_lines[idx]
                for v in line_violations:
                    word = _extract_misspelling(v.message)
                    if not word:
                        continue
                    lower = word.lower()
                    if lower not in typos:
                        continue
                    correction = typos[lower][0]
                    if word.isupper():
                        replacement = correction.upper()
                    elif word[0].isupper():
                        replacement = correction.capitalize()
                    else:
                        replacement = correction
                    current = re.sub(
                        rf"\b{re.escape(word)}\b",
                        replacement,
                        current,
                        count=1,
                    )
                fixed_lines[idx] = current

            fixed = "".join(fixed_lines)
            if fixed != original:
                confidence = AutofixConfidence.SAFE if all_safe else AutofixConfidence.SUGGEST
                results.append(
                    AutofixResult(
                        rule_id=self.rule_id,
                        file_path=path,
                        confidence=confidence,
                        original_content=original,
                        fixed_content=fixed,
                        description="Fixed misspellings",
                        violations_fixed=file_violations,
                    )
                )
        return results
