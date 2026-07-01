"""CLI for the skillsaw-typos plugin.

Installed as ``skillsaw-typos``, dispatched via ``skillsaw typos accept``.
"""

import argparse
import sys
from pathlib import Path

from skillsaw.context import RepositoryContext

from .rules import TypoRule, IGNORE_FILE


def cmd_accept(args):
    """Add all currently-flagged words to the ignore file."""
    repo = Path(args.path).resolve()
    context = RepositoryContext(repo)
    violations = TypoRule().check(context)

    words = set()
    for v in violations:
        parts = v.message.split("'")
        if len(parts) >= 2:
            words.add(parts[1].lower())

    if not words:
        print("No typo violations found — nothing to accept.")
        return 0

    ignore_path = repo / IGNORE_FILE
    existing = set()
    if ignore_path.exists():
        existing = {
            w.strip().lower()
            for w in ignore_path.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.strip().startswith("#")
        }

    new_words = words - existing
    if not new_words:
        print(f"All {len(words)} word(s) already in {IGNORE_FILE}.")
        return 0

    all_words = sorted(existing | words)
    ignore_path.write_text(
        "# Words accepted by `skillsaw typos accept`.\n"
        "# One word per line. Lines starting with # are comments.\n"
        + "".join(f"{w}\n" for w in all_words),
        encoding="utf-8",
    )
    print(f"Added {len(new_words)} word(s) to {IGNORE_FILE}: {', '.join(sorted(new_words))}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="skillsaw typos",
        description="Companion commands for the skillsaw-typos plugin",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    accept_parser = sub.add_parser(
        "accept",
        help="Accept all currently-flagged words into the ignore file",
    )
    accept_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository path (default: current directory)",
    )

    args = parser.parse_args()
    if args.command == "accept":
        return cmd_accept(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
