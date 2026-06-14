#!/usr/bin/env python3
"""Scan Java source for java-safe house-style violations and emit a report.

Machine-checkable coverage of the five conventions:
  - convention 4 (no `var`)          — Checkstyle, deterministic
  - convention 3 (final locals/params) — Checkstyle, deterministic
  - convention 1 (nullability)       — a subset: a missing @NullMarked default
  - convention 2 (minimal visibility) — a subset: a public top-level type with
                                        no cross-package import in the scan set
  - convention 5 (generics over Object) — NOT machine-checked (needs semantic
                                        judgment); shown as needs-review only

Conventions 1 and 2 cannot be verified in full by static analysis ("should this
return be @Nullable?" needs NullAway; "does this public API have a real external
caller?" needs precise symbol analysis). We check the reliable *subset* and the
report states the limits, so a clean run is never mistaken for full compliance.

Usage (run inside a venv so the system Python is never touched):
    python3 -m venv build/java-safe-venv
    build/java-safe-venv/bin/python -m scripts.scan <path-or-files...> \
        [--out build/reports/java-safe-report.html] [--format html|json] \
        [--fail-on-violations]

The Checkstyle JAR is fetched once to ~/.cache/java-safe/ on first run; set
CHECKSTYLE_JAR to point at an existing jar for offline use.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHECKSTYLE_VERSION = "13.5.0"
JAR_NAME = f"checkstyle-{CHECKSTYLE_VERSION}-all.jar"
# The runnable "fat" jar (with dependencies) is published on GitHub Releases.
# Maven Central only carries the thin jar, which cannot be run with `java -jar`.
MAVEN_URL = (
    "https://github.com/checkstyle/checkstyle/releases/download/"
    f"checkstyle-{CHECKSTYLE_VERSION}/{JAR_NAME}"
)

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "assets" / "java-safe-checks.xml"

DEFAULT_OUT = "build/reports/java-safe-report.html"

# Map a Checkstyle check class (the `source` attr in XML output) to convention.
SOURCE_TO_CONVENTION = {
    "RegexpSinglelineJava": 4,
    "FinalLocalVariable": 3,
    "FinalParameters": 3,
}

SKIP_DIRS = {"build", ".git", "target", "node_modules", "out", "bin"}

# ---------------------------------------------------------------------------
# Shared file-text cache (the nullability/visibility/snippet passes re-read).
# ---------------------------------------------------------------------------
_TEXT: dict[str, str] = {}


def file_text(path: Path) -> str:
    key = str(path)
    if key not in _TEXT:
        try:
            _TEXT[key] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            _TEXT[key] = ""
    return _TEXT[key]


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "java-safe"


def java_executable() -> str:
    """Locate a `java` binary, preferring JAVA_HOME.

    Non-interactive shells don't source the user's profile, so a bare `java`
    can resolve to an older system JDK. JAVA_HOME (when set) points at the real
    JDK; Checkstyle 13.x needs Java 21+, and an older java surfaces as a clear
    error from run_checkstyle rather than a cryptic LinkageError.
    """
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / "java"
        if candidate.is_file():
            return str(candidate)
    return "java"


def ensure_jar() -> Path:
    """Return a path to the Checkstyle jar, downloading it once if needed."""
    override = os.environ.get("CHECKSTYLE_JAR")
    if override:
        p = Path(override).expanduser()
        if p.is_file():
            return p
        sys.exit(f"CHECKSTYLE_JAR is set to {p} but no file is there.")

    cached = cache_dir() / JAR_NAME
    if cached.is_file():
        return cached

    cached.parent.mkdir(parents=True, exist_ok=True)
    print(
        f"Downloading Checkstyle {CHECKSTYLE_VERSION} (~18MB) to {cached} ...",
        file=sys.stderr,
    )
    try:
        tmp = cached.with_suffix(".part")
        with urllib.request.urlopen(MAVEN_URL) as resp, open(tmp, "wb") as fh:
            fh.write(resp.read())
        tmp.replace(cached)
    except Exception as exc:  # network restricted, etc.
        sys.exit(
            f"Could not download Checkstyle: {exc}\n"
            f"Download {JAR_NAME} manually from {MAVEN_URL}\n"
            f"then set CHECKSTYLE_JAR=/path/to/{JAR_NAME} and re-run."
        )
    return cached


def discover_java_files(paths: list[str]) -> list[Path]:
    """Expand the given paths into a sorted list of .java files."""
    found: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_file() and p.suffix == ".java":
            found.add(p.resolve())
        elif p.is_dir():
            for jf in p.rglob("*.java"):
                if any(part in SKIP_DIRS for part in jf.parts):
                    continue
                if "generated" in jf.parts:
                    continue
                found.add(jf.resolve())
    return sorted(found)


# ---------------------------------------------------------------------------
# Checkstyle pass — conventions 3 (final) and 4 (no var)
# ---------------------------------------------------------------------------
def run_checkstyle(jar: Path, files: list[Path]) -> str:
    """Run Checkstyle and return its XML output as a string."""
    with tempfile.NamedTemporaryFile(
        suffix=".xml", delete=False, mode="r", encoding="utf-8"
    ) as tmp:
        out_path = Path(tmp.name)
    cmd = [
        java_executable(), "-jar", str(jar),
        "-c", str(CONFIG_PATH),
        "-f", "xml",
        "-o", str(out_path),
        *[str(f) for f in files],
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if "UnsupportedClassVersionError" in proc.stderr:
        out_path.unlink(missing_ok=True)
        sys.exit(
            f"Checkstyle {CHECKSTYLE_VERSION} needs a newer Java than the one "
            f"found ({java_executable()}). Set JAVA_HOME to a JDK 21+ install "
            "and re-run."
        )
    xml_text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    out_path.unlink(missing_ok=True)
    # Checkstyle returns the violation count as its exit code, so non-zero is
    # normal. A non-zero exit with NO XML body means a real failure (bad config).
    if proc.returncode != 0 and "<file" not in xml_text:
        sys.exit(
            "Checkstyle failed to run:\n"
            + (proc.stderr.strip() or proc.stdout.strip() or "(no output)")
        )
    return xml_text


def parse_checkstyle(xml_text: str) -> list[dict]:
    """Parse Checkstyle XML into violation dicts (conventions 3 and 4)."""
    violations: list[dict] = []
    if not xml_text.strip():
        return violations
    root = ET.fromstring(xml_text)
    for file_el in root.findall("file"):
        fname = file_el.get("name", "")
        for err in file_el.findall("error"):
            source = err.get("source", "")
            convention = None
            for class_suffix, conv in SOURCE_TO_CONVENTION.items():
                if class_suffix in source:
                    convention = conv
                    break
            rule = source.rsplit(".", 1)[-1].split("#", 1)[0]
            if rule.endswith("Check"):
                rule = rule[: -len("Check")]
            violations.append({
                "file": fname,
                "line": int(err.get("line", "0") or 0),
                "column": int(err.get("column", "0") or 0),
                "rule": rule,
                "message": err.get("message", ""),
                "convention": convention,
            })
    return violations


# ---------------------------------------------------------------------------
# Convention 1 (nullability) — reliable subset: a missing @NullMarked default
# ---------------------------------------------------------------------------
_TYPE_DECL = re.compile(
    r"^\s*(?:public\s+|final\s+|abstract\s+|sealed\s+|non-sealed\s+)*"
    r"(?:class|interface|record|enum)\b"
)


def check_nullability(files: list[Path]) -> list[dict]:
    """Flag .java files that establish no @NullMarked default.

    A file is covered if it (or its package's package-info.java) carries
    @NullMarked. This is the part of convention 1 that is statically decidable;
    "this return should be @Nullable" still needs NullAway and is out of scope.
    """
    null_marked_pkgs: set[Path] = set()
    for f in files:
        if f.name == "package-info.java" and "@NullMarked" in file_text(f):
            null_marked_pkgs.add(f.parent)

    violations: list[dict] = []
    for f in files:
        if f.name == "package-info.java":
            continue
        text = file_text(f)
        if "@NullMarked" in text:
            continue
        if f.parent in null_marked_pkgs:
            continue
        line = 1
        for i, ln in enumerate(text.splitlines(), 1):
            if _TYPE_DECL.match(ln):
                line = i
                break
        violations.append({
            "file": str(f),
            "line": line,
            "column": 1,
            "rule": "MissingNullMarked",
            "message": (
                "No @NullMarked default established (neither this file nor its "
                "package-info.java) — convention 1."
            ),
            "convention": 1,
        })
    return violations


# ---------------------------------------------------------------------------
# Convention 2 (visibility) — reliable subset: public top-level type with no
# cross-package import anywhere in the scanned set
# ---------------------------------------------------------------------------
_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
_PUBLIC_TYPE = re.compile(
    r"^\s*public\s+(?:final\s+|abstract\s+|sealed\s+|non-sealed\s+)*"
    r"(?:class|interface|record|enum)\s+(\w+)"
)


def check_visibility(files: list[Path]) -> list[dict]:
    """Flag public top-level types that nothing outside their package imports.

    This is the statically-safe slice of convention 2: if no file in another
    package imports the type (by FQCN or a wildcard import of its package), the
    `public` modifier buys nothing within the scanned code and it could be
    package-private. It deliberately does NOT touch methods/fields, and it can
    over-flag entry points, reflection/DI, or SPI targets — the report says so.
    """
    pkg_of: dict[str, str] = {}
    for f in files:
        m = _PACKAGE.search(file_text(f))
        pkg_of[str(f)] = m.group(1) if m else ""

    public_types: list[tuple[Path, str, str, int]] = []
    for f in files:
        pkg = pkg_of[str(f)]
        for i, ln in enumerate(file_text(f).splitlines(), 1):
            m = _PUBLIC_TYPE.match(ln)
            if m:
                public_types.append((f, pkg, m.group(1), i))

    violations: list[dict] = []
    for (f, pkg, name, line) in public_types:
        fqcn = f"{pkg}.{name}" if pkg else name
        imported_fqcn = re.compile(rf"import\s+{re.escape(fqcn)}\s*;")
        imported_pkg = (
            re.compile(rf"import\s+{re.escape(pkg)}\.\*\s*;") if pkg else None
        )
        used = False
        for g in files:
            if g == f or pkg_of[str(g)] == pkg:
                continue  # same-package use does not justify `public`
            t = file_text(g)
            if imported_fqcn.search(t) or (imported_pkg and imported_pkg.search(t)):
                used = True
                break
        if not used:
            violations.append({
                "file": str(f),
                "line": line,
                "column": 1,
                "rule": "PublicTypeNoCrossPackageUse",
                "message": (
                    f"public type '{name}' has no cross-package import in the "
                    "scanned set — consider package-private (convention 2). "
                    "Verify it is not an entry point, reflection/DI, or SPI target."
                ),
                "convention": 2,
            })
    return violations


# ---------------------------------------------------------------------------
# Attach a source-code snippet to each violation (line +/- context)
# ---------------------------------------------------------------------------
def attach_snippets(violations: list[dict], context: int = 2) -> None:
    lines_cache: dict[str, list[str]] = {}
    for v in violations:
        fp = v["file"]
        if fp not in lines_cache:
            lines_cache[fp] = file_text(Path(fp)).splitlines()
        lines = lines_cache[fp]
        ln = v.get("line", 0)
        if ln <= 0 or not lines:
            v["snippet"] = []
            continue
        start = max(1, ln - context)
        end = min(len(lines), ln + context)
        v["snippet"] = [
            {"n": i, "text": lines[i - 1], "hit": i == ln}
            for i in range(start, end + 1)
        ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan Java for java-safe house-style violations."
    )
    parser.add_argument("paths", nargs="+", help="Java files or directories")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output path")
    parser.add_argument("--format", choices=["html", "json"], default="html")
    parser.add_argument(
        "--fail-on-violations", action="store_true",
        help="Exit non-zero if any violation is found",
    )
    args = parser.parse_args()

    files = discover_java_files(args.paths)
    if not files:
        sys.exit("No .java files found in the given paths.")

    jar = ensure_jar()
    violations = parse_checkstyle(run_checkstyle(jar, files))
    violations += check_nullability(files)
    violations += check_visibility(files)
    attach_snippets(violations)

    scan_data = {
        "checkstyle_version": CHECKSTYLE_VERSION,
        "files_scanned": [str(f) for f in files],
        "violations": violations,
    }

    if args.format == "json":
        out = Path(args.out)
        if out.suffix == ".html":
            out = out.with_suffix(".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(scan_data, indent=2), encoding="utf-8")
        out = out.resolve()
        print(f"JSON report: {out}")
    else:
        from scripts.report import write_report
        out = write_report(scan_data, Path(args.out)).resolve()
        print(f"HTML report: {out}")
        print(f"Open in a browser: {out.as_uri()}")

    n = len(violations)
    by_conv = {c: sum(1 for v in violations if v["convention"] == c) for c in (1, 2, 3, 4)}
    print(
        f"{n} machine-checkable violation(s) across {len(files)} file(s) "
        f"[conv1={by_conv[1]} conv2={by_conv[2]} conv3={by_conv[3]} conv4={by_conv[4]}]. "
        "Conventions 1 & 2 are checked as subsets and 5 is not machine-checked "
        "— see the report's coverage matrix.",
        file=sys.stderr,
    )
    if args.fail_on_violations and n:
        sys.exit(1)


if __name__ == "__main__":
    main()
