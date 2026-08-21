#!/usr/bin/env python3
"""End-to-end test of the npm package, against a real tarball in a sandbox HOME.

`npm publish` is irreversible: a published version number can never be reused.
This exercises the package the way a new user receives it, so a broken install
is caught while it is still fixable.

Every check runs against a throwaway HOME under a temporary directory. The real
agent directories are never read or written, so this is safe to run at any time.

    python3 scripts/test_package.py            # full run
    python3 scripts/test_package.py --keep     # keep the sandbox to poke at it

Requires: node and npm on PATH. No third-party Python packages.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skilllib import AGENT_TARGETS, POINTER_FILES, REPO_ROOT, discover

BIN_NAME = "sahil2004-skills"
MANAGED_BEGIN = "BEGIN managed skills index"


class Results:
    """Collects pass/fail so one failure does not hide the rest."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        if ok:
            self.passed += 1
            print(f"[  ok] {label}")
        else:
            self.failures.append(f"{label}{': ' + detail if detail else ''}")
            print(f"[fail] {label}")
            if detail:
                for line in detail.strip().splitlines()[:8]:
                    print(f"       {line}")
        return ok


def run(cmd, cwd=None, env=None, check=False):
    result = subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{result.stderr}")
    return result


def sandbox_env(home: Path) -> dict:
    """A HOME pointing into the sandbox, so no real agent directory is touched."""
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.pop("XDG_CONFIG_HOME", None)
    return env


def build_tarball(work: Path, r: Results) -> Path | None:
    """Pack the package exactly as `npm publish` would."""
    result = run(["npm", "pack", "--pack-destination", str(work)], cwd=REPO_ROOT)
    if result.returncode != 0:
        r.check(False, "npm pack succeeds", result.stderr)
        return None
    tarballs = sorted(work.glob("*.tgz"))
    if not r.check(bool(tarballs), "npm pack produces a tarball"):
        return None
    return tarballs[0]


def check_contents(tarball: Path, r: Results) -> None:
    """Every file each skill needs must be inside the tarball.

    The `files` allowlist in package.json is the usual way a skill ships
    half its references without anyone noticing.
    """
    listing = run(["tar", "-tzf", str(tarball)]).stdout
    packed = {line.split("/", 1)[1] for line in listing.splitlines() if "/" in line}

    missing = []
    for skill in discover():
        for path in skill.path.rglob("*"):
            if path.is_file() and not path.name.startswith("."):
                rel = path.relative_to(REPO_ROOT).as_posix()
                if rel not in packed:
                    missing.append(rel)
    r.check(not missing, "tarball contains every skill file", "\n".join(missing))

    r.check("bin/cli.js" in packed, "tarball contains the CLI")
    strays = [p for p in packed if p.startswith((".github/", "tests/")) or p.endswith(".pyc")]
    r.check(not strays, "tarball has no development cruft", "\n".join(strays))


def install_tarball(tarball: Path, home: Path, r: Results, label: str) -> bool:
    """Install the packed tarball into a sandbox, as a user would."""
    home.mkdir(parents=True, exist_ok=True)
    env = sandbox_env(home)
    run(["npm", "init", "-y"], cwd=home, env=env)
    result = run(["npm", "install", str(tarball)], cwd=home, env=env)
    return r.check(result.returncode == 0, f"npm install works ({label})", result.stderr)


def npx(home: Path, args: list[str]):
    return run([BIN_NAME, *args], cwd=home, env=sandbox_env(home))


def bin_path(home: Path) -> Path:
    return home / "node_modules" / ".bin" / BIN_NAME


def call_cli(home: Path, args: list[str]):
    """Invoke the installed binary directly; npx adds noise and network calls."""
    return run([str(bin_path(home)), *args], cwd=home, env=sandbox_env(home))


def check_install(home: Path, r: Results) -> None:
    r.check(bin_path(home).is_file(), f"binary is linked as {BIN_NAME}")

    result = call_cli(home, ["--all"])
    if not r.check(result.returncode == 0, "install runs cleanly", result.stderr):
        return

    for agent, target in AGENT_TARGETS.items():
        dest = Path(str(target).replace("~", str(home), 1))
        for skill in discover():
            if agent not in skill.targets():
                continue
            installed = dest / skill.name
            if not r.check(installed.is_dir(), f"{agent}: {skill.name} installed"):
                continue
            diff = filecmp.dircmp(skill.path, installed)
            mismatch = diff.left_only + diff.right_only + diff.diff_files
            r.check(
                not mismatch,
                f"{agent}: {skill.name} matches the repo byte for byte",
                " ".join(mismatch),
            )


def check_scripts_executable(home: Path, r: Results) -> None:
    """A shipped script that lost its +x bit fails only when a user runs it.

    The repo bit is asserted too, not merely used as a precondition: skipping
    when it is unset would turn the real failure into a silently absent check.
    """
    for skill in discover():
        for script in sorted((skill.path / "scripts").glob("*.sh")):
            r.check(
                os.access(script, os.X_OK),
                f"repo: {skill.name}/{script.name} is executable",
            )
            for agent, target in AGENT_TARGETS.items():
                if agent not in skill.targets():
                    continue
                dest = Path(str(target).replace("~", str(home), 1))
                installed = dest / skill.name / "scripts" / script.name
                if installed.is_file():
                    r.check(
                        os.access(installed, os.X_OK),
                        f"{agent}: {skill.name}/{script.name} stays executable",
                    )


def check_parity_with_python(tarball_home: Path, r: Results) -> None:
    """The Node CLI and install.py must produce the same tree.

    They duplicate the target table by necessity, so they can drift.
    """
    with tempfile.TemporaryDirectory() as tmp:
        py_home = Path(tmp)
        env = sandbox_env(py_home)
        result = run(
            [sys.executable, str(REPO_ROOT / "scripts" / "install.py"), "--all", "--copy"],
            cwd=REPO_ROOT,
            env=env,
        )
        if not r.check(result.returncode == 0, "install.py runs in a sandbox", result.stderr):
            return

        for agent, target in AGENT_TARGETS.items():
            rel = str(target).replace("~/", "")
            a, b = py_home / rel, tarball_home / rel
            if not (a.exists() and b.exists()):
                continue
            mismatch = _tree_diff(a, b)
            r.check(not mismatch, f"{agent}: Node CLI matches install.py", "\n".join(mismatch))

        for agent, pointer in POINTER_FILES.items():
            rel = str(pointer).replace("~/", "")
            a, b = py_home / rel, tarball_home / rel
            if not (a.is_file() and b.is_file()):
                continue
            # Each installer writes its own absolute HOME, so normalize before comparing.
            text_a = a.read_text(encoding="utf-8").replace(str(py_home), "HOME")
            text_b = b.read_text(encoding="utf-8").replace(str(tarball_home), "HOME")
            r.check(text_a == text_b, f"{agent}: pointer index matches install.py")


def _tree_diff(a: Path, b: Path) -> list[str]:
    """Files that differ between two trees, compared by content."""
    out = []
    for path in sorted(a.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(a)
        other = b / rel
        if not other.is_file():
            out.append(f"missing in node tree: {rel}")
        elif path.read_bytes() != other.read_bytes():
            out.append(f"differs: {rel}")
    for path in sorted(b.rglob("*")):
        if path.is_file() and not (a / path.relative_to(b)).is_file():
            out.append(f"unexpected in node tree: {path.relative_to(b)}")
    return out


def check_idempotent(home: Path, r: Results) -> None:
    """Re-running must not duplicate anything, since users re-run to upgrade."""
    before = _snapshot(home)
    result = call_cli(home, ["--all"])
    r.check(result.returncode == 0, "second run succeeds", result.stderr)
    r.check(before == _snapshot(home), "second run changes nothing")

    for agent, pointer in POINTER_FILES.items():
        path = Path(str(pointer).replace("~", str(home), 1))
        if path.is_file():
            count = path.read_text(encoding="utf-8").count(MANAGED_BEGIN)
            r.check(count == 1, f"{agent}: exactly one managed block, found {count}")


def _snapshot(home: Path) -> dict:
    out = {}
    for target in AGENT_TARGETS.values():
        root = Path(str(target).replace("~", str(home), 1))
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path.relative_to(home))] = path.read_bytes()
    return out


def check_preserves_user_content(home: Path, r: Results) -> None:
    """Everything outside the managed markers belongs to the user."""
    top, bottom = "USER CONTENT ABOVE\n", "\nUSER CONTENT BELOW\n"
    touched = []
    for agent, pointer in POINTER_FILES.items():
        path = Path(str(pointer).replace("~", str(home), 1))
        if not path.is_file():
            continue
        path.write_text(top + path.read_text(encoding="utf-8") + bottom, encoding="utf-8")
        touched.append((agent, path))

    call_cli(home, ["--all"])

    for agent, path in touched:
        text = path.read_text(encoding="utf-8")
        r.check(text.startswith(top), f"{agent}: content above the block survives")
        r.check(text.endswith(bottom), f"{agent}: content below the block survives")
        r.check(MANAGED_BEGIN in text, f"{agent}: managed block still written")


def check_selectors(home: Path, r: Results) -> None:
    """Bad input must fail loudly rather than silently installing nothing."""
    skill = discover()[0].name
    result = call_cli(home, ["--skill", skill, "--agent", "claude"])
    r.check(result.returncode == 0, f"--skill {skill} --agent claude works", result.stderr)

    result = call_cli(home, ["--skill", "definitely-not-a-skill"])
    r.check(result.returncode != 0, "unknown skill is rejected")
    r.check("available" in result.stdout + result.stderr, "unknown skill lists the real ones")

    result = call_cli(home, ["--agent", "definitely-not-an-agent"])
    r.check(result.returncode != 0, "unknown agent is rejected")
    r.check("known" in result.stdout + result.stderr, "unknown agent lists the real ones")


def check_engines(r: Results) -> None:
    """A declared Node floor must match the syntax actually used."""
    pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    floor = pkg.get("engines", {}).get("node")
    if not r.check(bool(floor), "package.json declares an engines.node floor"):
        return

    m = re.search(r"(\d+)", floor)
    major = int(m.group(1)) if m else 0
    source = (REPO_ROOT / "bin" / "cli.js").read_text(encoding="utf-8")
    # Features newer than the common floors, with the version that introduced them.
    modern = {
        "structuredClone(": 17,
        ".findLast(": 18,
        "fs.cpSync": 16,
        "node:test": 18,
        "Array.fromAsync": 22,
    }
    late = [f"{name} needs node >= {ver}" for name, ver in modern.items()
            if name in source and major < ver]
    r.check(not late, f"CLI syntax fits the declared floor ({floor})", "\n".join(late))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="keep the sandbox directory")
    args = parser.parse_args()

    for tool in ("node", "npm"):
        if not shutil.which(tool):
            print(f"{tool} is required but not on PATH")
            return 1

    r = Results()
    work = Path(tempfile.mkdtemp(prefix="skills-pkg-test-"))
    print(f"sandbox: {work}\n")

    try:
        tarball = build_tarball(work, r)
        if tarball is None:
            return 1
        print(f"tarball: {tarball.name}\n")

        check_contents(tarball, r)
        check_engines(r)

        home = work / "home"
        if install_tarball(tarball, home, r, "sandbox HOME"):
            check_install(home, r)
            check_scripts_executable(home, r)
            check_parity_with_python(home, r)
            check_idempotent(home, r)
            check_preserves_user_content(home, r)
            check_selectors(home, r)

        # A second, untouched HOME proves a first-time install needs no prior state.
        cold = work / "cold"
        if install_tarball(tarball, cold, r, "cold HOME"):
            result = call_cli(cold, ["--all"])
            r.check(result.returncode == 0, "cold install succeeds", result.stderr)
            found = sum(1 for _ in cold.rglob("SKILL.md")
                        if "node_modules" not in str(_))
            expected = sum(len(s.targets()) for s in discover())
            r.check(found == expected,
                    f"cold install writes every skill ({found}/{expected})")
    finally:
        if args.keep:
            print(f"\nsandbox kept at {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)

    print()
    if r.failures:
        print(f"{r.passed} passed, {len(r.failures)} FAILED")
        for f in r.failures:
            print(f"  - {f}")
        print("\nDo not publish until these pass.")
        return 1
    print(f"{r.passed} checks passed. Package is safe to publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
