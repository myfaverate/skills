# skills

为 Claude Code 及其他兼容的编码 agent 准备的 [Agent Skills](https://agentskills.io) 集合。

[English](README.md)

## 可用 Skills

| Skill | 说明 |
|---|---|
| [`rn-layered-feature`](rn-layered-feature/SKILL.zh.md) | React Native 功能模块的标准分层架构 —— 纯逻辑 / Hook / 视图三层分离 + 依赖注入，并强制「测试先行」的 TDD 流程。 |

## 安装

使用 [`skills`](https://github.com/vercel-labs/skills) CLI 安装（无需全局安装）：

```bash
# 安装指定 skill 到当前项目
npx skills add https://github.com/myfaverate/skills --skill rn-layered-feature

# 安装到全局（所有项目可用），仅装给 Claude Code，免确认
npx skills add https://github.com/myfaverate/skills --skill rn-layered-feature -g -a claude-code -y

# 仅列出本仓库的所有 skill，不安装
npx skills add https://github.com/myfaverate/skills --list
```

不安装、临时使用一次：

```bash
npx skills use https://github.com/myfaverate/skills --skill rn-layered-feature --agent claude-code
```

安装后，skill 会落到对应 agent 的 skills 目录（项目级如 `.claude/skills/`，全局如 `~/.claude/skills/`），agent 会在相关场景自动加载。

## 什么是 Agent Skill？

Skill 是一份可复用的指令集，定义在带 YAML frontmatter（`name` + `description`）的 `SKILL.md` 文件里。当任务匹配其描述时，agent 会自动启用它。详见 [agentskills.io](https://agentskills.io) 与 [Claude Code 官方文档](https://code.claude.com/docs/en/skills)。

## License

MIT
