#!/usr/bin/env python3
"""Append an import entry to an artifact's history in the bundle manifest.

    python3 record_import.py <bundle folder> <slug> --url <new artifact url> --label "<account label>"

Run after publishing, so the bundle carries the mapping from source url to the new url. A later
export from the importing account then updates the same bundle instead of starting a new one.
"""
import argparse, datetime, json, pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle"); ap.add_argument("slug"); ap.add_argument("--url", required=True); ap.add_argument("--label", required=True)
    a = ap.parse_args()
    mp = pathlib.Path(a.bundle) / "manifest.json"; m = json.loads(mp.read_text())
    entry = next((e for e in m["artifacts"] if e["slug"] == a.slug), None)
    if entry is None:
        raise SystemExit(f"record_import: no artifact {a.slug} in manifest")
    entry.setdefault("history", []).append({
        "action": "imported", "url": a.url, "label": a.label,
        "when": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    mp.write_text(json.dumps(m, indent=1))
    print(f"record_import: {a.slug} -> {a.url}")


if __name__ == "__main__":
    main()
