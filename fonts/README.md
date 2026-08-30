# fonts

Drop `.ttf` / `.otf` / `.ttc` files here, then run `../scripts/install.sh fonts`.

They install to `~/.local/share/fonts` on Linux and `~/Library/Fonts` on macOS, and the
font cache is refreshed automatically. This is the one module `backup.sh` will not
touch — fonts are vendored by hand, never exported from the machine.

Currently empty. `vscode/settings.json` asks for **JetBrains Mono**, which is not
vendored here and is not installed on this machine either — VS Code falls back to the
generic `monospace` family. `kitty/kitty.conf` sets a `font_size` but no `font_family`,
so kitty uses its own default. Either install the font from your package manager
(`sudo dnf install jetbrains-mono-fonts` on Fedora) or drop the `.ttf` files in here
and run the install script.

Check the license before committing a font. SIL OFL fonts (JetBrains Mono, Fira Code,
Cascadia Code, most Nerd Fonts) are redistributable; commercial fonts generally are not,
even in a private repo.
