# skillsaw-typos

A [skillsaw](https://skillsaw.org) plugin that flags misspellings in agentic
instruction prose using the [codespell](https://github.com/codespell-project/codespell)
known-typo dictionary.

## Installation

```bash
pip install skillsaw-typos
```

Once installed alongside skillsaw, the `typo` rule runs automatically — no
configuration required.

## What it checks

The `typo` rule walks every content block in the lint tree (CLAUDE.md, AGENTS.md,
skills, agents, prompts, etc.), reads prose with code fences stripped so
identifiers are never flagged, and checks each word against codespell's 64,000+
known misspellings.

### Fails

```markdown
- All handlers should recieve validated input from the middleware.
- Keep test files and source code in seperate directories.
```

```
⚠ WARNING (typo) [CLAUDE.md:5]: Misspelling: 'recieve' → 'receive'
⚠ WARNING (typo) [CLAUDE.md:6]: Misspelling: 'seperate' → 'separate'
```

### Passes

```markdown
- All handlers should receive validated input from the middleware.
- Keep test files and source code in separate directories.
```

Words inside fenced code blocks are never flagged.

## Autofix

```bash
skillsaw fix --rule typo
```

When codespell's dictionary has exactly one correction, the fix is applied
automatically (`SAFE`). When there are multiple candidates, the fix uses the
first suggestion and is marked `SUGGEST` — applied only with
`skillsaw fix --suggest`.

Fixes preserve the original word's casing (lowercase, Title Case, UPPER CASE).

## Configuration

In `.skillsaw.yaml`:

```yaml
rules:
  typo:
    enabled: true           # true | false | auto
    severity: warning        # error | warning | info
    ignore-words:            # words to accept (e.g. project jargon)
      - frobnicator
      - kubectl
    extra-dictionaries:      # additional dictionary files (codespell format)
      - .skillsaw/extra-typos.txt
```

### `ignore-words`

A list of words to skip even if they appear in the codespell dictionary.
Useful for project-specific jargon, product names, or intentional spellings.

### `extra-dictionaries`

Paths to additional dictionary files in codespell format (`word->correction`).
Each file is loaded on top of the built-in dictionary.

## Disabling

Per-rule:

```yaml
rules:
  typo:
    enabled: false
```

Entire plugin:

```yaml
plugins:
  disable:
    - typos
```

Or for a single run:

```bash
skillsaw lint --no-plugins
```
