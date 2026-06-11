# skills

A collection of [Agent Skills](https://agentskills.io) for Claude Code and other compatible coding agents.

[简体中文](README.zh.md)

## Available Skills

| Skill | Description |
|---|---|
| [`rn-layered-feature`](rn-layered-feature/SKILL.md) | Standard architecture for adding a React Native feature module — pure-logic / hook / view three-layer separation + dependency injection, with mandatory test-first TDD. |
| [`react-layered-feature`](react-layered-feature/SKILL.md) | The pure-web React sibling of `rn-layered-feature` — same pure-reducer state machine, hook, and DI layering over browser APIs (`MediaRecorder`, Permissions API), with mandatory test-first TDD. |

## Install

Install with the [`skills`](https://github.com/vercel-labs/skills) CLI (no global install required):

```bash
# Install a specific skill into the current project
npx skills add myfaverate/skills --skill rn-layered-feature
npx skills add myfaverate/skills --skill react-layered-feature

# Install globally (available across all projects), for Claude Code, no prompts
npx skills add myfaverate/skills --skill rn-layered-feature -g -a claude-code -y
npx skills add myfaverate/skills --skill react-layered-feature -g -a claude-code -y

# List all skills in this repo without installing
npx skills add myfaverate/skills --list
```

Use a skill once without installing it:

```bash
npx skills use myfaverate/skills --skill rn-layered-feature --agent claude-code
npx skills use myfaverate/skills --skill react-layered-feature --agent claude-code
```

After installing, the skill lands in your agent's skills directory (e.g. `.claude/skills/` for project scope, `~/.claude/skills/` for global) and the agent loads it automatically when relevant.

## What is an Agent Skill?

A skill is a reusable instruction set defined in a `SKILL.md` file with YAML frontmatter (`name` + `description`). The agent activates it automatically when the task matches the description. Learn more at [agentskills.io](https://agentskills.io) and the [Claude Code skills docs](https://code.claude.com/docs/en/skills).

## License

MIT
