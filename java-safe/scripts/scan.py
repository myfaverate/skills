#!/usr/bin/env python3
"""Scan Java source for java-safe house-style violations and emit a report.

Wraps Checkstyle (the machine-checkable subset of the four conventions:
no `var` and `final` locals/params) and renders an honest HTML report that
flags nullability and visibility as "needs review" rather than pretending to
verify them.

Usage:
    python -m scripts.scan <path-or-files...> [--out report.html]
                           [--format html|json] [--fail-on-violations]

The Checkstyle JAR is fetched once to ~/.cache/java-safe/ on first run; set
CHECKSTYLE_JAR to point at an existing jar for offline use.
"""

import argparse
import json
import os
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

# Map a Checkstyle check class (the `source` attr in XML output, e.g.
# "...checks.coding.FinalLocalVariableCheck") to the convention it enforces.
# Checkstyle emits the class name, not the configured id, so we match by the
# class-name suffix.
SOURCE_TO_CONVENTION = {
    "RegexpSinglelineJava": 4,
    "FinalLocalVariable": 3,
    "FinalParameters": 3,
}

SKIP_DIRS = {"build", ".git", "target", "node_modules", "out", "bin"}


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "java-safe"


def java_executable() -> str:
    """Locate a `java` binary, preferring JAVA_HOME.

    The Bash tool runs non-interactive shells that don't source ~/.zshrc, so a
    bare `java` can resolve to an older system JDK. JAVA_HOME (when set) points
    at the user's real JDK, so prefer $JAVA_HOME/bin/java and fall back to PATH.
    Checkstyle 13.x requires Java 21+; an older java surfaces as a clear error
    from run_checkstyle rather than a cryptic LinkageError.
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
        f"Downloading Checkstyle {CHECKSTYLE_VERSION} (~15MB) to {cached} ...",
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
    # Checkstyle exits non-zero when it finds violations; that is expected and
    # not an error for us — we read the XML it produced either way.
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
    # normal. But a non-zero exit with NO XML body means a real failure (e.g. a
    # bad config) — surface it instead of reporting a false "0 violations".
    if proc.returncode != 0 and "<file" not in xml_text:
        sys.exit(
            "Checkstyle failed to run:\n"
            + (proc.stderr.strip() or proc.stdout.strip() or "(no output)")
        )
    return xml_text


def parse_violations(xml_text: str) -> list[dict]:
    """Parse Checkstyle XML into a flat list of violation dicts."""
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
            # source looks like "...FinalParametersCheck#JavaSafeFinalParam";
            # show a clean check name (drop the package, the #id, and Check).
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan Java for java-safe house-style violations."
    )
    parser.add_argument(
        "paths", nargs="+", help="Java files or directories to scan"
    )
    parser.add_argument(
        "--out", default="java-safe-report.html", help="Output path"
    )
    parser.add_argument(
        "--format", choices=["html", "json"], default="html"
    )
    parser.add_argument(
        "--fail-on-violations", action="store_true",
        help="Exit non-zero if any machine-checkable violation is found",
    )
    args = parser.parse_args()

    files = discover_java_files(args.paths)
    if not files:
        sys.exit("No .java files found in the given paths.")

    jar = ensure_jar()
    xml_text = run_checkstyle(jar, files)
    violations = parse_violations(xml_text)

    scan_data = {
        "checkstyle_version": CHECKSTYLE_VERSION,
        "files_scanned": [str(f) for f in files],
        "violations": violations,
    }

    if args.format == "json":
        out = Path(args.out)
        if out.suffix == ".html":
            out = out.with_suffix(".json")
        out.write_text(json.dumps(scan_data, indent=2), encoding="utf-8")
        print(f"Wrote JSON to {out}")
    else:
        from scripts.report import write_report
        out = write_report(scan_data, Path(args.out))
        print(f"Wrote HTML report to {out}")

    n = len(violations)
    print(
        f"{n} machine-checkable violation(s) across {len(files)} file(s). "
        "Nullability (conv 1) and visibility (conv 2) are NOT machine-checked "
        "— see the report's coverage matrix.",
        file=sys.stderr,
    )
    if args.fail_on_violations and n:
        sys.exit(1)


if __name__ == "__main__":
    main()
