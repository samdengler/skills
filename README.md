# Skills

Agent Skills for Claude. This repo is a Claude Code plugin marketplace; each skill installs as its own plugin.

| Skill | Description |
| --- | --- |
| [artifact-exchange](skills/artifact-exchange) | Export Claude artifacts into a portable zip bundle and import them into another Claude account. |

## Install in Claude Code

```
/plugin marketplace add samdengler/skills
/plugin install artifact-exchange@samdengler-skills
```

## Install in claude.ai or Claude Desktop

Zip the skill folder and upload it as a custom skill in Settings:

```
cd skills && zip -r artifact-exchange.zip artifact-exchange
```

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter.
2. Add a plugin entry for it in `.claude-plugin/marketplace.json`.
3. Run `claude plugin validate .`
