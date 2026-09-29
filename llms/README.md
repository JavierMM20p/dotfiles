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

The repository is authoritative for global personal skills. Installation removes
entries absent from `llms/skills/` from `~/.agents/skills` and
`~/.claude/skills`, including account-synced skills. It also clears legacy personal
skills from `$CODEX_HOME/skills` (default `~/.codex/skills`), preserving only
Codex's bundled `.system` directory. Plugin-managed skills outside these directories
are unaffected. Credentials, sessions, history, and generated memories are not
imported into this repository.

## Settings

`settings.toml` is this repository's input format, translated by `scripts/llms.py`.
It is not a file either client reads directly.

| Shared preference | Supported values | Codex key | Claude key |
| --- | --- | --- | --- |
| `shared.reasoning_effort` | `low`, `medium`, `high` | `model_reasoning_effort` | `effortLevel` |

The initial model choices preserve this machine's preferences: `gpt-6-astra` and
`opus`. The same effort label expresses a preference, not identical computation
or output across models.

In user settings, Opus 5.5 and later Claude models ignore the top-level
`effortLevel` and read a per-model entry under `modelSettings` instead. That entry
is managed natively in `[claude.modelSettings.claude-opus-5-5]`; keep it in step
with `shared.reasoning_effort` when changing either.

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

### Token usage

Most plan usage in agentic coding comes from input: every request re-sends the
whole conversation, including earlier tool output. Long contexts also lower answer
quality, so these settings aim to keep reasoning and context proportional to the
task.

| Setting | Effect |
| --- | --- |
| `shared.reasoning_effort = "medium"`, Opus 5.5 `effortLevel = "medium"` | Fewer thinking tokens on routine work; Anthropic's default for Opus 5.5 |
| `codex.plan_mode_reasoning_effort = "high"` | Codex plan mode keeps deeper reasoning |
| `codex.agents.default_subagent_reasoning_effort = "medium"` | Spawned Codex agents otherwise default to `xhigh` on `gpt-6-astra` |
| `codex.model_auto_compact_token_limit = 150000` | Compacts at 150K tokens instead of near the 272K window; requests above 100K made up 58% of measured Codex input |
| `claude.autoCompactWindow = 400000` | Compacts at 400K tokens instead of about 967K on 1M-context models |
| `claude.env.CLAUDE_CODE_SUBAGENT_MODEL = "sonnet"` | Subagents without their own model use Sonnet; built-in Explore and Plan agents are unaffected |

Raise effort for hard tasks without changing the saved default:
`claude --effort high`, the `s` key in the `/effort` slider (session only), or
`ultrathink` in a single prompt. In Codex, use
`codex -c model_reasoning_effort=high`. Plain `/effort high` in Claude Code saves
the level to `modelSettings`, which `check` then reports as drift. On Opus 5.5,
changing effort mid-session keeps the prompt cache; switching models does not.

Codex already truncates each tool output to 10K tokens for `gpt-6-astra`, so
`tool_output_token_limit` is not set. Tool-output compressors are deliberately
not used: a
[controlled Claude Code study](https://arxiv.org/abs/2607.12161) found that
cutting tool-output tokens by 38.4% raised billed cost by 6.8% through extra turns
and re-reads.

Habits matter more than settings: `/clear` between unrelated tasks, name the files
and a way to verify the result in each prompt, and `/rewind` instead of correcting
a wrong path in place. `/usage` shows cache hit rate and which skills, subagents,
and MCP servers use the most.

## Instructions and skills

### Repository attribution

The shared instructions prohibit assistant and provider attribution in commit
messages, pull requests, repository descriptions, and repository files. They
exclude AI co-author trailers, session links, signatures, and generated-by notices,
while preserving necessary technical references and third-party license notices.
Existing Git identities and history are preserved.

`settings.toml` also disables Claude Code's native attribution with
`attribution.commit = ""`, `attribution.pr = ""`, and
`attribution.sessionUrl = false`; see the
[Claude Code attribution settings](https://code.claude.com/docs/en/settings-reference#attribution).
Codex receives the rule through the shared `AGENTS.md`. These are global defaults;
project or organization configuration can take precedence. Reinstall the LLM
configuration and restart the clients to load the changes.

### No emojis

The shared instructions prohibit emojis in replies and newly authored content,
including commits, pull requests, documentation, and code comments. Exact quotations,
literal output, and data that must remain unchanged are preserved. This rule does
not authorize removing existing emojis from files.

### Conversational writing and code comments

`instructions.md` contains shared preferences for the assistants' conversational
replies. The writing guidance applies to explanations, progress updates, questions,
and summaries, and to prose in comments and docstrings written or edited during a
task. Comments should be sparse, short, and direct, explaining non-obvious reasons
or constraints without narrating the code. Required documentation and useful
technical detail remain intact.

Executable code, literal examples, commands, tool directives, and data are
excluded from the style pass. The guidance does not authorize unrelated rewrites
of existing comments or other artifacts. Project instructions can further
specialize that guidance.
A nonempty Codex `AGENTS.override.md` takes
precedence over `AGENTS.md`; `check` reports it so you can reconcile it yourself.

### Humanizer research and adaptation

The writing preferences were informed by
[blader/humanizer](https://github.com/blader/humanizer), reviewed on 2026-09-20 at
revision [`9862685`](https://github.com/blader/humanizer/tree/9862685f575c65a8247f90369951df1b3416e3d6)
(skill version 3.0.0, MIT license). Its behavior is defined in
[`SKILL.md`](https://github.com/blader/humanizer/blob/9862685f575c65a8247f90369951df1b3416e3d6/SKILL.md):
the agent identifies writing patterns, drafts a rewrite, checks both style and
preservation of claims, and produces the final text. It groups 25 patterns around
staged phrasing, repetitive rhythm, inflated claims, decorative formatting, and
leftover chatbot language. Its pattern list draws on Wikipedia's "Signs of AI
writing." The repository also provides agent/plugin metadata and a package
validation script; the model performs the editing from Markdown instructions.

This setup uses independently worded, shorter guidance in the shared instruction
file so it applies to ordinary replies without invoking a skill. It keeps the
clarity and factual-preservation principles, applies them to conversation and
comment or docstring prose, and makes the review silent. Upstream's default
pasted-text mode displays a draft, critique, and final rewrite, and its file mode
can edit prose in files. Those
behaviors are outside this adaptation. Punctuation and formatting remain choices
based on readability, with useful technical structure preserved.

These are model instructions, not an output filter or an AI detector. Compliance
can vary with the model and other active instructions. Restart both clients after
installing. To spot-check in a new session, request an explanation with a code
sample and confirm that the prose is direct and the code follows its language and
project conventions. No Humanizer plugin, runtime dependency, or external editing
service is required.

### Shared skills

Add a directory under `skills/` containing `SKILL.md` with `name` and `description`
YAML frontmatter and the workflow in Markdown. Two skills are bundled:
`c4-mermaid-diagrams` generates, reviews, and repairs C4 architecture diagrams in
Mermaid, and `frontend-design` guides visual direction, typography, and layout when
building or reshaping a user interface. Use lowercase letters, digits, and hyphens
for names (up to 64 characters); `synced` is reserved by Claude Code.

Keep shared skills portable: prefer ordinary instructions and supporting scripts
over tool-specific invocation controls, tool names, inline command expansion, or
subagent metadata. Supporting scripts retain executable bits. Nested symlinks
inside a skill are rejected; the installer can link the whole skill directory.

Invoke a skill by name: `$c4-mermaid-diagrams` in Codex, `/c4-mermaid-diagrams` in
Claude. Automatic discovery still depends on each client's behavior and the task.

After adding, removing, or renaming a skill, install again. Both copy and symlink
installation remove extra entries and update repository skills. An empty source
skills directory removes all installed personal skills. Removed entries are moved
to the installation backup, with their original locations recorded in its manifest.
Use `--dry-run` to preview removals. Global skills directories must be real
directories; symlinked roots are rejected before changes to avoid pruning an
external tree. Individual skill symlinks can be replaced or removed safely.

## Checking and backing up

`python3 scripts/llms.py check` compares managed settings and shared content with
both installations. Exit status is zero when they match and nonzero for drift,
missing files, extra global skills, invalid configuration, or a shadowing Codex
instruction file.
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

Replaced files and removed skills are saved in a gitignored `.config-backup-*-llms-*/` directory, with
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
