#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List exactly what would be published, and refuse anything that should not be.

The project directory also holds confidential material - the working paper, the
prior-art gate and the corporate document build engine. The .gitignore uses a deny-by-default
allowlist, but a mistake there would be expensive and silent. This script states the
result in plain terms instead, and fails loudly on anything unexpected.

    python3 scripts/check_publish.py            # list what is public
    python3 scripts/check_publish.py --strict   # exit non-zero on any violation
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PUBLIC_FILES = {".gitignore", "LICENSE", "LICENSE-DATA", "CITATION.cff",
                "CONTRIBUTING.md", "README.md", "index.html"}
PUBLIC_DIRS = {".github", "rpt", "driven-states", "scripts"}

# Anything matching these must never be published, wherever it sits.
FORBIDDEN_SUFFIX = (".docx", ".pdf", ".zip", ".key", ".pem", ".env")
FORBIDDEN_SUBSTR = ("Arbeitspapier", "Prior-Art", "Gate", "NDA", "Vertrag",
                    "Rechnung", "Angebot", "eigenart_ci", "Satzprobe")
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "proof"}


def walk_public():
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        if os.path.isfile(path) and name in PUBLIC_FILES:
            yield name
        elif os.path.isdir(path) and name in PUBLIC_DIRS:
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for fn in sorted(filenames):
                    if fn == ".DS_Store":
                        continue
                    yield os.path.relpath(os.path.join(dirpath, fn), ROOT)


def main():
    strict = "--strict" in sys.argv
    public = list(walk_public())
    violations = []
    for rel in public:
        base = os.path.basename(rel)
        if base.endswith(FORBIDDEN_SUFFIX) or any(s in rel for s in FORBIDDEN_SUBSTR):
            violations.append(rel)

    by_dir = {}
    for rel in public:
        by_dir.setdefault(rel.split(os.sep)[0] if os.sep in rel else "(root)", []).append(rel)

    print("Files that would be published (%d):\n" % len(public))
    for d in sorted(by_dir):
        print("  %-18s %d file(s)" % (d, len(by_dir[d])))

    withheld = [n for n in sorted(os.listdir(ROOT))
                if n not in PUBLIC_FILES and n not in PUBLIC_DIRS
                and not n.startswith(".DS")]
    print("\nWithheld from publication (%d top-level items):" % len(withheld))
    for n in withheld:
        print("  %s" % n)

    if violations:
        print("\nVIOLATION - these must not be published:")
        for v in violations:
            print("  ! %s" % v)
        if strict:
            return 1
    else:
        print("\nNo forbidden file inside the published set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
