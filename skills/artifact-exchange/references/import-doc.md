# Importing Claude Docs

A `kind: "doc"` artifact is rebuilt as a real Claude Doc through the Claude Docs connector.  Publishing its
markdown or HTML with the Artifact tool makes a page, not a Doc, so never do that.

Tools: mcp__Claude_Docs__batch and __update (always loaded), __read and __create (ToolSearch "select:..."),
the Artifact tool (open, read, and one asset upload per doc when it has images), Bash, Read.
If no mcp__Claude_Docs__ tools exist in this account, say so and stop: the doc cannot become a Doc here.
Offer the tab markdown under `tabs/` as plain files instead.

Every Artifact upload asks the person for approval, one prompt per call.  Never upload markdown to carry
text into a doc; write text inline in `update` calls.  Images go up in one `file_paths` call per doc.

S = the skill's `scripts/` folder.  B = the unpacked bundle.  For each doc, `artifacts/<slug>/doc.json`
lists its tabs in order, with each tab's markdown, widgets, images and byline date.

## 1. Create every doc first, empty

Do this for all docs before writing content, so links between them can point at the new urls (step 2).
One `batch` per doc births it with every tab and a placeholder paragraph in each:

```
batch(container={"kind":"project","create":{"name":"<doc.json name>",
        "doc":{"markdown":"Content is being imported."}}},
      batch=[ for each tab after the first, three members:
        {"$lid":"f2","verb":"create","object":"file","payload":{"value":{"birthName":"<Tab name>.ldoc"}}},
        {"$lid":"n2","verb":"create","object":"node","engine":"prose",
         "payload":{"parent":{"object":"file","id":"$lid:f2"},
                    "source":{"as":"markdown","from":{"kind":"inline","content":"Content is being imported."}}}},
        {"verb":"update","ref":{"object":"file","id":"$lid:f2"},
         "payload":{"kind":"value","value":{"birthName":"<Tab name>.ldoc","content":{"kind":"node","id":"$lid:n2"}}}},
      then one member that names and orders every tab, the first one included:
        {"verb":"update","ref":{"object":"project","id":"$lid:p"},"payload":{"kind":"patch","patch":[
          {"op":"set","path":["tabs","$lid:f"],"value":{"name":"<first tab name>","order":"a0"}},
          {"op":"set","path":["tabs","$lid:f2"],"value":{"name":"<second tab name>","order":"a1"}} ]}} ])
```

(`birthName` may not contain `/`.)  The ack gives the doc's link and each tab's file id and body id; a
`read(ref={"object":"project","id":<id>})` confirms them.  Read each body's outline once to get the
placeholder paragraph's id, `h` and `rev`.  Then record the doc right away:
`python3 S/record_import.py B <slug> --url <new link> --label "<this account label>"`.

## 2. Repoint links between bundled artifacts

`python3 S/rewrite_links.py B "<this account label>"` rewrites every link to another bundled artifact's
origin url to its new url, in all tab markdown.  It lists links to artifacts outside the bundle; those stay
pointing at the origin account, so name them in the final report.

## 3. Images and blobs

For a doc with files under `assets/`: one `Artifact(action="publish", url=<new doc link>, asset=true,
file_paths=[...every image...])`.  For each new asset id, `create(object="blob", engine="blob",
container=C, payload={"asset":"<new asset id>"})` gives a new blob id.  Write `map.json` as
`{"blob/<old blob id>": "blob/<new blob id>"}` (old ids are in doc.json `pictures[].blob` and
`widgets[].blobs`) and run `python3 S/rewrite_assets.py B/artifacts/<slug> map.json`.

## 4. Widgets (diagrams and charts)

For each tab, each widget in doc.json order: Read `widgets/<node>.tsx` and
`create(object="node", engine="widget", container=C, payload={"parent":{"object":"file","id":<new tab file id>},
"code":<the file's text exactly>})`.  The ack must say outcome "published"; keep its `minted` id for that
widget's token (w1, w2, ...).  A validation error means the code was changed in transit: Read the file again
and resend it exactly.

## 5. Text, in pieces

`python3 S/doc_chunk.py B/artifacts/<slug>/<tab file> B/work/<slug>/<NN>` splits the tab into parts and
prints each part's tokens.  Write the parts in order, one `update` per part, on the tab's body node:

- part01 replaces the placeholder:
  `{"op":"replace","target":{"kind":"blocks","ids":["<placeholder id>"]},"ifHash":"<h>","ifRev":<rev>,
   "with":{"as":"markdown","blocks":{...},"from":{"kind":"inline","content":"<part text exactly>"}}}`
- each later part appends:
  `{"op":"insert","target":{"kind":"root"},"side":"end",
   "source":{"as":"markdown","blocks":{...},"from":{"kind":"inline","content":"<part text exactly>"}}}`
- `blocks` holds only the tokens that part uses, and is left out when it uses none:
  `asof` → `{"type":"date","value":"<tab asof>"}`, `me` → `{"type":"mention","user":"me"}`,
  `wN` → `{"type":"embed","ref":"node/<minted id>","caption":"<caption>"}`.
- Copy each part's text exactly: two spaces after periods, backslash escapes such as `\_` and `\[`, quotes
  escaped for JSON.
- A refusal (`row_too_large`, often dim `fragment_links`) lands nothing.  Split that part at a blank line
  outside a table, send both pieces in order, and never resend a part that already landed.

Several docs can be filled in parallel, one sub-agent per doc, each given this file and its slug.

## 6. Check each tab against its source

Export each new tab: `create(object="blob", engine="blob", container=C, payload={"from":{"object":"file",
"id":<tab file id>},"format":"markdown"})`, save it with `Artifact(action="read", url=<new link>, path=<asset>)`,
then `python3 S/doc_compare.py B/artifacts/<slug>/<tab raw file> <saved export>`.  It ignores link targets and
blob ids.  Any differing line is a transcription slip: fix that block with a targeted `update`
(topic.editing in the Docs guide), then compare again.  Report a tab as imported only at 0 differing lines.
