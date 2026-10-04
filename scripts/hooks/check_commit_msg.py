"""commit-msg hook: enforce conventional commits, forbid AI attribution trailers (CONTRIBUTING)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|chore|test|refactor|perf|build|ci|style|revert)(\([a-z0-9_\-/]+\))?!?: .+"
)
FORBIDDEN = re.compile(
    r"co-authored-by:.*(claude|anthropic|gpt|openai|copilot|gemini|cursor|codeium)"
    r"|generated with \[?claude|🤖 generated",
    re.IGNORECASE,
)


def main(argv: list[str]) -> int:
    text = Path(argv[0]).read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    subject = lines[0] if lines else ""
    errors = []
    if not subject.startswith(("Merge ", "Revert ")) and not CONVENTIONAL.match(subject):
        errors.append(
            "Subject must follow conventional commits, e.g. 'feat(planning): add publish gate'."
        )
    if FORBIDDEN.search(text):
        errors.append("AI attribution trailers are not allowed (see CONTRIBUTING: git workflow).")
    for e in errors:
        print(f"commit-msg: {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
