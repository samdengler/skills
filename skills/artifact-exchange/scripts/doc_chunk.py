#!/usr/bin/env python3
"""Split one prepared tab's markdown into pieces small enough for one Docs write each.

    python3 doc_chunk.py <tab.md> <out folder> [--bytes 3000] [--links 14]

A Docs write that carries in-page links ([text](#heading)) is refused with row_too_large
(dim fragment_links) when one write holds too many of them or too much text, and nothing lands.
Pieces break only at blank lines, never inside a table, list, or code fence, so each piece
is whole markdown. One block bigger than the limits becomes a piece of its own.

Writes part01.md, part02.md, ... and prints, per part: bytes, in-page link count, and the
<?claude block KEY?> tokens it holds, which the import passes in that write's "blocks" map.
"""
import argparse, os, re


def blocks(md):
    out, cur, fence = [], [], False
    for line in md.split("\n"):
        if line.startswith("```"):
            fence = not fence
        if line.strip() == "" and not fence:
            if cur:
                out.append("\n".join(cur)); cur = []
            continue
        cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--bytes", type=int, default=3000); ap.add_argument("--links", type=int, default=14)
    a = ap.parse_args()
    md = open(a.src, encoding="utf-8").read()
    links = lambda s: len(re.findall(r"\]\(#", s))
    parts, cur = [], ""
    for b in blocks(md):
        nxt = (cur + "\n\n" + b) if cur else b
        if cur and (len(nxt.encode()) > a.bytes or links(nxt) > a.links):
            parts.append(cur); cur = b
        else:
            cur = nxt
    if cur:
        parts.append(cur)
    os.makedirs(a.out, exist_ok=True)
    for i, p in enumerate(parts, 1):
        open(os.path.join(a.out, f"part{i:02d}.md"), "w", encoding="utf-8").write(p + "\n")
        print(f"part{i:02d}.md bytes={len(p.encode())} links={links(p)} tokens={re.findall(r'<\?claude block (\w+)\?>', p)}")


if __name__ == "__main__":
    main()
