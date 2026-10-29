#!/usr/bin/env python3
"""Check an imported Docs tab against the tab it came from.

    python3 doc_compare.py <original export.md> <imported export.md>

Both files are markdown exports from the Docs connector (a blob created from the tab with
format "markdown", saved with an Artifact read). Before comparing, it blanks what is expected
to differ between two docs: in-page link targets, blob ids, and links to other bundled
artifacts (rewritten on import). Prints the number of differing lines and the first few;
exits 1 when any differ.
"""
import difflib, re, sys


def norm(t):
    t = re.sub(r"\]\(#[^)]*\)", "](#)", t)
    t = re.sub(r"blob/[0-9a-f-]+", "blob/", t)
    t = re.sub(r"https://claude\.ai/(code/)?artifact/[A-Za-z0-9-]+", "ARTIFACT", t)
    return t.splitlines()


def main(a, b):
    x, y = norm(open(a, encoding="utf-8").read()), norm(open(b, encoding="utf-8").read())
    diff = [l for l in difflib.unified_diff(x, y, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    print(f"doc_compare: {len(diff)} differing line(s)")
    for l in diff[:20]:
        print("  " + l[:200])
    sys.exit(1 if diff else 0)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
