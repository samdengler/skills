# {{BUNDLE_NAME}} bundle

Exported {{EXPORTED_AT}} from {{ORIGIN_LABEL}} with the artifact-exchange skill.

## Contents

{{ARTIFACT_LINES}}

Skills included: {{SKILLS}}

## To import into another Claude account

Install the artifact-exchange skill there if it is not installed, or replace an older copy with the one in skills/artifact-exchange.zip: only a copy with `references/import-doc.md` rebuilds Claude Docs as Docs instead of pages. Claude Docs also need the Claude Docs connector in that account. Attach this bundle to a conversation and paste:

```
The attached {{BUNDLE_NAME}}-bundle.zip is an artifact exchange bundle. Use the artifact-exchange skill to import it. This account is "{{TARGET_LABEL}}". Create each artifact here (or update it, if the manifest history shows it was imported here before), keep every file as the bundle holds it, then send me the updated bundle and a table of source url to new url.
```

## To send edits back

In the account where the edits were made, attach this bundle and paste:

```
Use the artifact-exchange skill to export the artifacts listed in the attached bundle's manifest from this account, updating the bundle in place, and send me the new zip.
```
