#!/usr/bin/env python3
"""Assemble or unpack an artifact exchange bundle.

    python3 bundle.py pack   <folder> <out.zip>     # validate manifest, zip the folder
    python3 bundle.py unpack <bundle.zip> <folder>  # unzip and print the manifest summary
    python3 bundle.py init   <folder> "<bundle name>"   # create a folder with an empty manifest

Bundle layout (see SKILL.md):
  manifest.json
  README.md
  artifacts/<slug>/...        one folder per artifact
  skills/<name>.zip           skills the artifacts depend on (optional)
"""
import json, pathlib, sys, zipfile, datetime

MANIFEST_VERSION = 1


def load_manifest(folder):
    p = pathlib.Path(folder) / "manifest.json"
    if not p.exists():
        sys.exit(f"bundle: no manifest.json in {folder}")
    return json.loads(p.read_text())


def validate_doc(slug, base):
    """A Claude Doc: doc.json names every tab's markdown, widget code and image."""
    errs = []
    dj = base / "doc.json"
    if not dj.exists():
        return [f"{slug}: a doc artifact needs doc.json"]
    d = json.loads(dj.read_text())
    if not d.get("tabs"):
        errs.append(f"{slug}: doc.json lists no tabs")
    for t in d.get("tabs", []):
        if not (base / t.get("file", "")).exists():
            errs.append(f"{slug}: tab {t.get('name')!r}: markdown not found: {t.get('file')}")
        text = (base / t["file"]).read_text() if (base / t.get("file", "")).exists() else ""
        for w in t.get("widgets", []):
            if not (base / w["file"]).exists():
                errs.append(f"{slug}: tab {t.get('name')!r}: widget code not found: {w['file']}")
            if f"<?claude block {w['token']}?>" not in text:
                errs.append(f"{slug}: tab {t.get('name')!r}: token {w['token']} not in its markdown")
        for p in t.get("pictures", []):
            if not (base / p["asset_file"]).exists():
                errs.append(f"{slug}: tab {t.get('name')!r}: image not found: {p['asset_file']}")
        if "embedded content:" in text or "&#91;image:" in text:
            errs.append(f"{slug}: tab {t.get('name')!r}: export placeholders left; run doc_prep_tab.py")
    return errs


def validate(folder):
    folder = pathlib.Path(folder)
    m = load_manifest(folder)
    errors = []
    if m.get("bundle_version") != MANIFEST_VERSION:
        errors.append(f"bundle_version must be {MANIFEST_VERSION}")
    for a in m.get("artifacts", []):
        slug = a.get("slug")
        base = folder / "artifacts" / (slug or "")
        if not slug or not base.is_dir():
            errors.append(f"artifact {a.get('title')!r}: missing folder artifacts/{slug}")
            continue
        if a.get("kind") not in ("page", "typed", "doc"):
            errors.append(f"{slug}: kind must be 'page', 'typed' or 'doc'")
        for f in a.get("files", []):
            if not (base / f).exists():
                errors.append(f"{slug}: listed file not found: {f}")
        for asset in a.get("assets", []):
            if not (base / asset["file"]).exists():
                errors.append(f"{slug}: asset file not found: {asset['file']}")
        if a.get("kind") == "page" and "index.html" not in a.get("files", []):
            errors.append(f"{slug}: a page artifact must list index.html")
        if a.get("kind") == "doc":
            errors.extend(validate_doc(slug, base))
        if a.get("kind") == "typed" and not a.get("type"):
            errors.append(f"{slug}: a typed artifact needs 'type' (e.g. Slides)")
    for s in m.get("skills", []):
        if not (folder / "skills" / s).exists():
            errors.append(f"skill zip not found: skills/{s}")
    return m, errors


def pack(folder, out):
    m, errors = validate(folder)
    if errors:
        sys.exit("bundle: manifest problems:\n  " + "\n  ".join(errors))
    folder = pathlib.Path(folder)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(folder))
    n = sum(1 for p in folder.rglob("*") if p.is_file())
    print(f"bundle: wrote {out} ({n} files, {len(m['artifacts'])} artifact(s): "
          + ", ".join(a['slug'] for a in m['artifacts']) + ")")


def unpack(zip_path, folder):
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(folder)
    m, errors = validate(folder)
    print(f"bundle: {m.get('name')} exported {m.get('exported_at')} from {m.get('origin', {}).get('label', 'unknown')}")
    for a in m["artifacts"]:
        kind = a["kind"] + (f" ({a['type']})" if a.get("type") else "")
        if a["kind"] == "doc":
            d = json.loads((pathlib.Path(folder) / "artifacts" / a["slug"] / "doc.json").read_text())
            kind += ", tabs: " + ", ".join(t["name"] for t in d["tabs"])
        print(f"  - {a['slug']}: {a['title']!r}, {kind}, {len(a.get('files', []))} file(s), {len(a.get('assets', []))} asset(s)")
        for h in a.get("history", []):
            print(f"      {h.get('when')}: {h.get('action')} at {h.get('label')} -> {h.get('url')}")
    if errors:
        print("bundle: problems:\n  " + "\n  ".join(errors))


def init(folder, name):
    folder = pathlib.Path(folder)
    (folder / "artifacts").mkdir(parents=True, exist_ok=True)
    m = {"bundle_version": MANIFEST_VERSION, "name": name,
         "exported_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
         "origin": {"label": ""}, "artifacts": [], "skills": []}
    (folder / "manifest.json").write_text(json.dumps(m, indent=1))
    print(f"bundle: initialized {folder}/manifest.json")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    {"pack": pack, "unpack": unpack, "init": init}[cmd](sys.argv[2], sys.argv[3])
