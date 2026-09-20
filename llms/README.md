# Shared LLM configuration

One source for global Codex and Claude Code settings, instructions, and skills.
Requires Python 3.11+; there are no third-party Python dependencies.

```bash
./scripts/install.sh --dry-run llms
./scripts/install.sh llms                 # copy instructions and skills
./scripts/install.sh --symlink llms       # edit shared content directly through either tool
python3 scripts/llms.py check
./scripts/backup.sh llms
```

The module also runs when installing or backing up all modules. Neither CLI needs
to be installed to prepare its configuration. Restart the clients after installing.
Installation configures local clients; it does not install the clients or sign in.

## Sources and destinations

| Repository source | Codex | Claude Code |
| --- | --- | --- |
| `settings.toml` | Merge into `~/.codex/config.toml` | Merge into `~/.claude/settings.json` |
| `instructions.md` | `~/.codex/AGENTS.md` | `~/.claude/CLAUDE.md` |
| `skills/<name>/` | `~/.agents/skills/<name>/` | `~/.claude/skills/<name>/` |

`CODEX_HOME` overrides the Codex settings/instructions directory;
`CLAUDE_CONFIG_DIR` overrides the Claude directory. Codex's personal skills remain
under `~/.agents/skills`, independently of `CODEX_HOME`.

Only individual curated skills are installed. Existing system, plugin, account
synced, and unrelated personal skills are left in place. Credentials, sessions,
history, and generated memories are not imported into this repository.

## Settings

`settings.toml` is this repository's input format, translated by `scripts/llms.py`.
It is not a file either client reads directly.

| Shared preference | Supported values | Codex key | Claude key |
| --- | --- | --- | --- |
| `shared.reasoning_effort` | `low`, `medium`, `high` | `model_reasoning_effort` | `effortLevel` |

The initial model choices preserve this machine's preferences: `gpt-6-astra` and
`opus`. The same effort label expresses a preference, not identical computation
or output across models.

Put additional native settings under `[codex]` or `[claude]`. Nested tables work:

```toml
[claude.permissions]
defaultMode = "default"
```

Only declared keys are managed. Nested tables merge recursively; arrays replace
as a whole. Unrelated values, including local project trust and MCP definitions,
are preserved. Removing a key from the source stops managing it; it does not
delete the installed value. Native keys are passed through; use each client's
documentation to choose supported values. Empty managed nested tables are rejected.

Permissions and sandboxing have different semantics in the two tools, so they
stay native. No permission settings are changed by the initial configuration.
Editor-specific settings remain in `vscode/settings.json`.

Generated settings are always regular files, even with `--symlink`. If a settings
file needs updating, it is parsed and rewritten: values are preserved, but TOML
comments and formatting are not. Unchanged settings files are not rewritten.
Existing settings symlinks are backed up and replaced without editing their targets.
Keep secrets in local configuration or environment variables, not in this source.

## Instructions and skills

`instructions.md` starts blank, ready for your personal guidance in all projects. Project instructions
can further specialize that guidance. A nonempty Codex `AGENTS.override.md` takes
precedence over `AGENTS.md`; `check` reports it so you can reconcile it yourself.

Add a directory under `skills/` containing `SKILL.md` with `name` and `description`
YAML frontmatter and the workflow in Markdown. The only bundled skill, `c4-mermaid-diagrams`, generates, reviews, and repairs C4
architecture diagrams in Mermaid. Use lowercase letters, digits, and hyphens for names (up to
64 characters); `synced` is reserved by Claude Code.

Keep shared skills portable: prefer ordinary instructions and supporting scripts
over tool-specific invocation controls, tool names, inline command expansion, or
subagent metadata. Supporting scripts retain executable bits. Nested symlinks
inside a skill are rejected; the installer can link the whole skill directory.

Invoke the skill as `$c4-mermaid-diagrams` in Codex or `/c4-mermaid-diagrams` in Claude.
Automatic discovery still depends on each client's behavior and the task.

After adding a skill, install again. Removing or renaming a source skill does not
automatically remove old installed copies or links: remove those individual entries
from both destinations yourself. Entire skills directories are never replaced.

## Checking and backing up

`python3 scripts/llms.py check` compares managed settings and shared content with
both installations. Exit status is zero when they match and nonzero for drift,
missing files, invalid configuration, or a shadowing Codex instruction file.
It checks files, not the effective settings of a running client: project settings,
CLI flags, model-specific overrides, editor settings, and managed policies may
still affect behavior.

`./scripts/backup.sh llms` exports only declared settings and curated content.
Both tools must have the same shared effort, instructions, and corresponding
skill contents. Missing files or conflicting edits abort the LLM export before
any repository file is changed. Align the two copies, or edit the repository and
reinstall, then retry. Native settings such as model choices export independently.
New local settings and skills must first be deliberately added to the source;
backup never scrapes whole tool directories.

With symlinks, instruction and skill edits already reach the source. Settings
still need backup. To preview an export, use:

```bash
python3 scripts/llms.py backup --dry-run
```

Replaced files are saved in a gitignored `.config-backup-*-llms-*/` directory, with
`manifest.jsonl` recording their original locations. This includes previous source
files replaced during backup. Repeated installations with unchanged inputs do
nothing. Preflight catches configuration and content errors before changes; an OS
error during application can leave a partial installation, recoverable from these
backups. Stop editing the configuration while installing or exporting it.

Run the isolated tests with `python3 -m unittest discover -s tests -v`.

## Official references

- [Codex settings](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Codex global instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code settings](https://code.claude.com/docs/en/settings)
- [Claude Code instructions](https://code.claude.com/docs/en/memory)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
