"""Regenerate the SYNTHETIC demonstration fixtures from ``trading_scanner.synthetic``.

Usage (from the project root, inside the virtual environment):

    python scripts/generate_synthetic_fixtures.py          # write files
    python scripts/generate_synthetic_fixtures.py --check  # fail if files are stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_scanner.config import PACKAGED_FIXTURE_DIR
from trading_scanner.synthetic import demo_scenarios

TARGET = PACKAGED_FIXTURE_DIR / "synthetic"


def rendered() -> dict[Path, str]:
    return {
        TARGET / f"{scenario.symbol.lower()}.json": json.dumps(scenario.document(), indent=2) + "\n"
        for scenario in demo_scenarios()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify files are current without writing")
    args = parser.parse_args(argv)
    files = rendered()
    stale = [path for path, text in files.items() if not path.exists() or path.read_text() != text]
    extra = sorted(set(TARGET.glob("*.json")) - set(files))
    if args.check:
        for path in stale + extra:
            print(f"stale: {path}")
        return 1 if stale or extra else 0
    TARGET.mkdir(parents=True, exist_ok=True)
    for path in extra:
        path.unlink()
    for path, text in files.items():
        path.write_text(text)
    print(f"wrote {len(files)} synthetic fixtures to {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
