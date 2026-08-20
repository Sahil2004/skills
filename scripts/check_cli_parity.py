#!/usr/bin/env python3
"""Check that bin/cli.js stays in sync with the Python installer.

The npm CLI duplicates the target table and pointer-file table by necessity:
it must run with no Python and no dependencies. This asserts the duplicates
still agree, so a target added in one place cannot silently go missing in the
other.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skilllib import AGENT_TARGETS, POINTER_FILES, REPO_ROOT

CLI = REPO_ROOT / "bin" / "cli.js"


def js_table(source: str, name: str) -> dict:
    """Extract a `const NAME = { ... };` object literal from the CLI."""
    m = re.search(rf"const {name} = \{{(.*?)\n\}};", source, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        km = re.match(r'"?([\w-]+)"?:\s*"([^"]+)"', line)
        if km:
            out[km.group(1)] = km.group(2)
    return out


def main() -> int:
    errors = []

    if not CLI.is_file():
        print("bin/cli.js not found")
        return 1
    source = CLI.read_text(encoding="utf-8")

    for name, expected in (("AGENT_TARGETS", AGENT_TARGETS), ("POINTER_FILES", POINTER_FILES)):
        actual = js_table(source, name)
        if actual != expected:
            for key in sorted(set(expected) | set(actual)):
                if expected.get(key) != actual.get(key):
                    errors.append(
                        f"{name}[{key}]: python={expected.get(key)!r} node={actual.get(key)!r}"
                    )

    pkg_path = REPO_ROOT / "package.json"
    if pkg_path.is_file():
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        binaries = pkg.get("bin", {})
        for target in binaries.values():
            if not (REPO_ROOT / target).is_file():
                errors.append(f"package.json bin points at missing file: {target}")
        for entry in ("bin/", "skills/"):
            if entry not in pkg.get("files", []):
                errors.append(f"package.json files[] is missing {entry!r}")
    else:
        errors.append("package.json not found")

    # The CLI must run without any dependency install.
    if (REPO_ROOT / "package.json").is_file():
        result = subprocess.run(
            ["node", str(CLI), "--list"], capture_output=True, text=True
        )
        if result.returncode != 0:
            errors.append(f"node bin/cli.js --list failed: {result.stderr.strip()}")

    for e in errors:
        print(f"[fail] {e}")
    if errors:
        print(f"\n{len(errors)} error(s)")
        return 1
    print("[  ok] bin/cli.js matches scripts/skilllib.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
