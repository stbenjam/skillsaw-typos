"""Skillsaw plugin that flags misspellings in agentic instruction prose."""

from .rules import TypoRule

SKILLSAW_RULES = [TypoRule]
