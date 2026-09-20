# dotfiles

My machine setup as code — VS Code, zsh, kitty, and the fonts they ask for.
Clone it on a new machine, run one script, get the same environment.

## Layout

Each top-level directory is a **module**: the files it owns, laid out under a name
matching the tool. `scripts/` knows where each module's files belong on a real machine.

```
vscode/
  settings.json      -> <VS Code User dir>/settings.json
  keybindings.json   -> <VS Code User dir>/keybindings.json
  snippets/          -> <VS Code User dir>/snippets/
  extensions.txt     extension IDs, one per line
zsh/
  zshrc              -> ~/.zshrc
kitty/
  kitty.conf         -> ~/.config/kitty/kitty.conf
fonts/               .ttf/.otf files -> ~/.local/share/fonts (~/Library/Fonts on macOS)
scripts/
  install.sh         repo    -> machine
  backup.sh          machine -> repo
  common.sh          module registry + path autodetection
```

Files are stored without their leading dot (`zsh/zshrc`, not `zsh/.zshrc`) so they are
visible in a plain `ls` and in file trees. The dot is added when installing.

## Set up a new machine

```bash
git clone git@github.com:JavierMM20p/dotfiles.git ~/system-configuration/dotfiles
cd ~/system-configuration/dotfiles
./scripts/install.sh
```

Existing config is not overwritten blindly — anything already in place is moved into
`.config-backup-<timestamp>/` at the repo root (gitignored) before being replaced.

Options:

| Flag | Effect |
| --- | --- |
| `--symlink` | Symlink instead of copying, so edits made in the app write straight back to the repo |
| `--no-extensions` | Skip VS Code extension installation |
| `--dry-run` | Print what would happen, change nothing |

Pass module names to narrow it down:

```bash
./scripts/install.sh zsh kitty      # shell + terminal only
./scripts/install.sh --symlink      # everything, as symlinks
./scripts/install.sh fonts
```

`--symlink` is the low-friction choice on your main machine: edit `~/.zshrc` or VS Code
settings as usual, then just `git diff` and commit. Plain copy is safer on machines
where you want local divergence.

## Kitty pane shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+Shift+Arrow` | Create a pane in that direction |
| `Alt+Shift+Arrow` | Focus the neighboring pane |
| `Ctrl+Shift+Enter` | Create a split with an automatically chosen direction |
| `Ctrl+Shift+W` | Close the focused pane |

New panes inherit the current directory. Directional creation uses the default
`splits` layout. `Ctrl+Shift+Up/Down` replace single-line scrolling; use
`Ctrl+Shift+PageUp/PageDown` to scroll by pages. Reload configuration in Kitty with
`Ctrl+Shift+F5`.

## Save changes back

```bash
./scripts/backup.sh                 # or: ./scripts/backup.sh zsh
git diff                            # review
git commit -am "Update zsh config"
git push
```

Not needed for tracked files if you installed with `--symlink`, but still required
after installing or removing VS Code extensions, since those live in the editor's own
state rather than in a file.

`fonts` is install-only — `backup.sh` refuses it, because font files are vendored
deliberately rather than scraped off whatever happens to be installed.

## Adding a new module

One place to edit: `module_files()` in [scripts/common.sh](scripts/common.sh). Add the
name to `ALL_MODULES` and a case branch printing `<repo path>\t<machine path>` per file.
`install.sh` and `backup.sh` both walk that map, in opposite directions, so neither
needs to change.

## Machine-specific paths

The scripts autodetect the VS Code User directory for Linux, macOS, Windows (Git Bash),
Insiders, Flatpak, and VSCodium, and honour `XDG_CONFIG_HOME` for kitty. If yours is
somewhere else, override it:

```bash
VSCODE_USER_DIR="$HOME/some/other/User" ./scripts/install.sh
CODE_CLI=code-insiders ./scripts/install.sh
```

## Fonts

`vscode/settings.json` sets:

```jsonc
"editor.fontFamily": "'JetBrains Mono', monospace",
"editor.fontLigatures": true
```

**JetBrains Mono is not committed to `fonts/`, and it is not installed on this machine
either** — VS Code is currently falling back to the generic `monospace` family. To
actually get the font:

- **Package manager** (Fedora): `sudo dnf install jetbrains-mono-fonts`, or
- **Vendored in this repo**: drop the `.ttf` files into `fonts/` and run
  `./scripts/install.sh fonts`. JetBrains Mono is SIL OFL 1.1, so redistributing it
  here is fine.

Until one of those happens, the `fontFamily` setting is inert on a fresh machine, and
`kitty.conf` sets a size but no family.

Check font licenses before committing them to any repo, private or not — most open
fonts (SIL OFL) are fine to redistribute, commercial ones usually are not.

## VS Code theme

The look is JetBrains-flavoured and comes from two standalone extensions, both in
`extensions.txt`:

| Setting | Value | Provided by |
| --- | --- | --- |
| `workbench.colorTheme` | JetBrains Darcula Theme | `anan.jetbrains-darcula-theme` |
| `workbench.iconTheme` | vscode-jetbrains-icon-theme | `chadalen.vscode-jetbrains-icon-theme` |

Drop either extension and VS Code silently falls back to Dark+ / the Seti icons.

## zsh dependencies

`zsh/zshrc` sources three things from system paths and silently skips each if absent,
so it works on a bare machine — but you get a plainer shell:

| Feature | Fedora package |
| --- | --- |
| fzf key bindings | `fzf` |
| autosuggestions | `zsh-autosuggestions` |
| syntax highlighting | `zsh-syntax-highlighting` |
| `z`-style jumping | `zoxide` |

```bash
sudo dnf install fzf zsh-autosuggestions zsh-syntax-highlighting zoxide
```

The syntax-highlighting block must stay last in `zshrc` — it wraps the line editor and
misses anything defined after it.

## What is deliberately not tracked

Machine-local, churn-heavy, or secret-bearing state stays out (see `.gitignore`):

- `globalStorage/`, `workspaceStorage/`, `History/` — per-machine VS Code state and auth tokens
- `.zsh_history` — personal, and a common place for secrets typed on a command line
- `*.local` — the conventional name for per-machine overrides you source but do not share
- `.vscode/` project-level settings — those belong in each project's own repo

## Note on the settings in here

`vscode/settings.json` enables `claudeCode.allowDangerouslySkipPermissions` and sets
`initialPermissionMode` to `bypassPermissions`. That is intentional on a personal
machine, but it means any machine you run `install.sh` on inherits it. Worth a second
thought before syncing to a shared or work box.
