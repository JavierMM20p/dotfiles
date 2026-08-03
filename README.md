# vscode-config

My VS Code setup as code — settings, keybindings, snippets, extensions, and fonts.
Clone it on a new machine, run one script, get the same editor.

## Layout

```
vscode/
  settings.json      user settings
  keybindings.json   custom keybindings
  snippets/          user snippets
  extensions.txt     extension IDs, one per line
fonts/               font files (.ttf/.otf) to install
scripts/
  install.sh         repo  -> machine
  backup.sh          machine -> repo
  install-fonts.sh   installs fonts/ into the user font dir
```

## Set up a new machine

```bash
git clone git@github.com:JavierMM20p/vscode-config.git
cd vscode-config
./scripts/install.sh
```

Existing config is not overwritten blindly — anything already in place is moved to
`.config-backup-<timestamp>/` inside the VS Code User directory first.

Options:

| Flag | Effect |
| --- | --- |
| `--symlink` | Symlink instead of copying, so edits in VS Code write straight back to the repo |
| `--no-extensions` | Skip extension installation |
| `--dry-run` | Print what would happen, change nothing |

`--symlink` is the low-friction choice on your main machine: edit settings in VS Code,
then just `git diff` and commit. Plain copy is safer on machines where you want local
divergence.

## Save changes back

```bash
./scripts/backup.sh
git diff            # review
git commit -am "Update settings"
git push
```

Not needed for `settings.json` / `keybindings.json` / `snippets` if you installed with
`--symlink`, but still required after installing or removing extensions.

## Fonts

`fonts/` is empty — this machine has no custom fonts installed and no
`editor.fontFamily` set, so VS Code is using the platform default.

To add one (e.g. a Nerd Font patched for terminal glyphs):

1. Drop the `.ttf`/`.otf` files into `fonts/`.
2. Run `./scripts/install-fonts.sh`.
3. Add the family to `vscode/settings.json`, then `./scripts/install.sh`:

```jsonc
"editor.fontFamily": "JetBrainsMono Nerd Font, 'Ubuntu Mono', monospace",
"editor.fontLigatures": true,
"terminal.integrated.fontFamily": "JetBrainsMono Nerd Font"
```

Check font licenses before committing them to any repo, private or not — most open
fonts (SIL OFL) are fine to redistribute, commercial ones usually are not.

## Theme

`workbench.colorTheme` is set to **Spinel**, which ships inside the
`shopify.ruby-extensions-pack` extension rather than as a standalone theme. It is in
`extensions.txt`, so `install.sh` pulls it in automatically. If you ever drop that
extension pack, the theme goes with it and VS Code falls back to Dark+.

## Different VS Code install layouts

The scripts autodetect the User directory for Linux, macOS, Windows (Git Bash),
Insiders, Flatpak, and VSCodium. If yours is somewhere else, override it:

```bash
VSCODE_USER_DIR="$HOME/some/other/User" ./scripts/install.sh
CODE_CLI=code-insiders ./scripts/install.sh
```

## What is deliberately not tracked

Machine-local and churn-heavy state stays out (see `.gitignore`):

- `globalStorage/`, `workspaceStorage/`, `History/` — per-machine state and auth tokens
- `.vscode/` project-level settings — those belong in each project's own repo

## Note on the settings in here

`settings.json` enables `claudeCode.allowDangerouslySkipPermissions` and sets
`initialPermissionMode` to `bypassPermissions`. That is intentional on a personal
machine, but it means any machine you run `install.sh` on inherits it. Worth a second
thought before syncing to a shared or work box.
