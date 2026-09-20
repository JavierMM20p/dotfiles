#!/usr/bin/env python3
"""Install, check, and export the shared LLM domain (Python 3.11+)."""

import argparse
import copy
import datetime
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

try:
    import tomllib
except ImportError:
    sys.exit("error: the llms module requires Python 3.11 or newer")


REPO = Path(__file__).resolve().parent.parent
MISSING = object()
EFFORT_KEYS = {"codex": "model_reasoning_effort", "claude": "effortLevel"}


def read_settings(path, tool="codex"):
    if not path.exists():
        if path.is_symlink():
            raise ValueError(f"broken settings symlink: {path}")
        return {}
    text = path.read_text()
    data = json.loads(text) if tool == "claude" else tomllib.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"settings must be an object: {path}")
    return data


def leaves(data, prefix=()):
    for key, value in data.items():
        path = prefix + (key,)
        if isinstance(value, dict):
            if not value:
                raise ValueError(f"empty managed table: {'.'.join(path)}")
            yield from leaves(value, path)
        else:
            yield path, value


def get(data, path):
    for key in path:
        if not isinstance(data, dict) or key not in data:
            return MISSING
        data = data[key]
    return data


def put(data, path, value):
    for key in path[:-1]:
        if key not in data:
            data[key] = {}
        if not isinstance(data[key], dict):
            raise ValueError(f"cannot merge table over existing scalar: {'.'.join(path)}")
        data = data[key]
    data[path[-1]] = value


def toml_value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{toml_key(k)} = {toml_value(v)}" for k, v in value.items()) + " }"
    raise ValueError(f"unsupported TOML value type: {type(value).__name__}")


def toml_key(key):
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else json.dumps(key, ensure_ascii=False)


def dump_toml(data):
    lines = []

    def table(values, path=()):
        if path:
            lines.extend(["", "[" + ".".join(toml_key(k) for k in path) + "]"])
        for key, value in values.items():
            if not isinstance(value, dict):
                lines.append(f"{toml_key(key)} = {toml_value(value)}")
        for key, value in values.items():
            if isinstance(value, dict):
                table(value, path + (key,))

    table(data)
    result = "\n".join(lines).lstrip("\n") + "\n"
    # Verify the serializer before ever replacing a user's configuration.
    tomllib.loads(result)
    return result


def load_source(root):
    source = read_settings(root / "settings.toml")
    if set(source) != {"shared", "codex", "claude"}:
        raise ValueError("settings.toml must contain [shared], [codex], and [claude]")
    if any(not isinstance(value, dict) for value in source.values()):
        raise ValueError("settings sections must be tables")
    if set(source["shared"]) != {"reasoning_effort"}:
        raise ValueError("[shared] supports exactly reasoning_effort")
    if source["shared"]["reasoning_effort"] not in ("low", "medium", "high"):
        raise ValueError("shared.reasoning_effort must be low, medium, or high")
    native = {}
    for tool, effort_key in EFFORT_KEYS.items():
        if effort_key in source[tool]:
            raise ValueError(f"set {effort_key} through shared.reasoning_effort")
        native[tool] = copy.deepcopy(source[tool])
        native[tool][effort_key] = source["shared"]["reasoning_effort"]
        list(leaves(native[tool]))
    return source, native


def snapshot(path):
    """Compare contents and executable bits; allow a symlink only at the root."""
    if not path.exists():
        raise ValueError(f"missing file or directory: {path}")
    if path.is_file():
        return ("file", path.read_bytes(), path.stat().st_mode & 0o111)
    if not path.is_dir():
        raise ValueError(f"unsupported file type: {path}")
    result = {}
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            raise ValueError(f"nested symlinks are not supported in shared skills: {child}")
        name = str(child.relative_to(path))
        if child.is_dir():
            result[name] = ("directory",)
        elif child.is_file():
            result[name] = ("file", child.read_bytes(), child.stat().st_mode & 0o111)
        else:
            raise ValueError(f"unsupported file type: {child}")
    return ("directory", result)


def same_contents(left, right):
    return right.exists() and snapshot(left) == snapshot(right)


class Domain:
    def __init__(self, repo):
        self.repo = repo
        self.root = repo / "llms"
        self.source, self.native = load_source(self.root)
        home = Path.home()
        codex = Path(os.environ.get("CODEX_HOME") or home / ".codex").expanduser().absolute()
        claude = Path(os.environ.get("CLAUDE_CONFIG_DIR") or home / ".claude").expanduser().absolute()
        self.settings = {"codex": codex / "config.toml", "claude": claude / "settings.json"}
        self.override = codex / "AGENTS.override.md"
        self.content = [(self.root / "instructions.md", [codex / "AGENTS.md", claude / "CLAUDE.md"])]
        for skill in sorted((self.root / "skills").iterdir()):
            if not skill.is_dir():
                continue
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill.name) or len(skill.name) > 64 or skill.name == "synced":
                raise ValueError(f"invalid or reserved skill name: {skill.name}")
            if not (skill / "SKILL.md").is_file():
                raise ValueError(f"missing SKILL.md: {skill}")
            self.content.append((skill, [home / ".agents/skills" / skill.name, claude / "skills" / skill.name]))
        for source, _ in self.content:
            snapshot(source)

    def plan_install(self, symlink):
        actions = []
        for tool, target in self.settings.items():
            current = read_settings(target, tool)
            merged = copy.deepcopy(current)
            changed = []
            for path, value in leaves(self.native[tool]):
                if get(current, path) != value:
                    changed.append(".".join(path))
                    put(merged, path, value)
            if changed:
                text = json.dumps(merged, indent=2, ensure_ascii=False, allow_nan=False) + "\n" if tool == "claude" else dump_toml(merged)
                actions.append(("write", target, text, f"merge {tool} settings: {', '.join(changed)}"))
        for source, targets in self.content:
            for target in targets:
                if symlink:
                    matches = target.is_symlink() and target.resolve() == source.resolve()
                else:
                    matches = not target.is_symlink() and same_contents(source, target)
                if not matches:
                    actions.append(("link" if symlink else "copy", target, source, f"{source.relative_to(self.repo)}"))
        return actions

    def differences(self):
        differences = []
        for tool, target in self.settings.items():
            current = read_settings(target, tool)
            for path, value in leaves(self.native[tool]):
                if get(current, path) != value:
                    differences.append(f"{tool}: {'.'.join(path)} differs or is missing")
        for source, targets in self.content:
            for target in targets:
                if not same_contents(source, target):
                    differences.append(f"{target}: differs from {source.relative_to(self.repo)} or is missing")
        if self.override.is_file() and self.override.read_text().strip():
            differences.append(f"{self.override} shadows the shared Codex instructions")
        return differences

    def plan_backup(self):
        # Validate every shared value before exporting anything to the repository.
        current = {tool: read_settings(path, tool) for tool, path in self.settings.items()}
        values = [get(current[tool], (key,)) for tool, key in EFFORT_KEYS.items()]
        if MISSING in values or values[0] != values[1]:
            raise ValueError("conflicting or missing reasoning effort; align both tools before backup")
        if values[0] not in ("low", "medium", "high"):
            raise ValueError("installed reasoning effort is outside the shared low/medium/high range")
        exported = copy.deepcopy(self.source)
        exported["shared"]["reasoning_effort"] = values[0]
        for tool in EFFORT_KEYS:
            for path, _ in leaves(self.source[tool]):
                value = get(current[tool], path)
                if value is MISSING:
                    raise ValueError(f"missing managed setting: {tool}.{'.'.join(path)}")
                put(exported[tool], path, value)
        actions = []
        if exported != self.source:
            actions.append(("write", self.root / "settings.toml", dump_toml(exported), "export managed settings only"))
        for source, targets in self.content:
            if snapshot(targets[0]) != snapshot(targets[1]):
                raise ValueError(f"conflicting copies of {source.relative_to(self.repo)}; align both tools before backup")
            if not same_contents(targets[0], source):
                actions.append(("copy", source, targets[0], f"export {source.relative_to(self.repo)}"))
        return actions


def apply(repo, actions, dry_run):
    backup = None
    for index, (kind, target, payload, description) in enumerate(actions):
        print(f"  {'would ' if dry_run else ''}{kind} {target} ({description})")
        if dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = stat.S_IMODE(target.stat().st_mode) if target.is_file() else 0o600
        # Prepare the replacement before moving the previous file out of the way.
        with tempfile.TemporaryDirectory(prefix=".llms-", dir=target.parent) as staging:
            staged = Path(staging) / "replacement"
            if kind == "write":
                staged.write_text(payload)
                staged.chmod(mode)
            elif kind == "link":
                staged.symlink_to(payload, target_is_directory=payload.is_dir())
            elif payload.is_dir():
                shutil.copytree(payload, staged)
            else:
                shutil.copy2(payload, staged)
            if target.exists() or target.is_symlink():
                if backup is None:
                    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    backup = Path(tempfile.mkdtemp(prefix=f".config-backup-{stamp}-llms-", dir=repo))
                old = backup / f"{index}-{target.name}"
                shutil.move(str(target), old)
                with (backup / "manifest.jsonl").open("a") as manifest:
                    manifest.write(json.dumps({"original": str(target), "backup": old.name}) + "\n")
            staged.replace(target)
    if backup:
        print(f"Previous files saved to: {backup}")
    if not actions:
        print("  already up to date")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "check", "backup"))
    parser.add_argument("--dry-run", action="store_true", help="preview install or backup without writing")
    parser.add_argument("--symlink", action="store_true", help="link instructions and individual skills on install")
    args = parser.parse_args()
    if args.symlink and args.command != "install":
        parser.error("--symlink applies only to install")
    try:
        domain = Domain(REPO)
        if args.command == "check":
            differences = domain.differences()
            for difference in differences:
                print(f"  drift: {difference}")
            if not differences:
                print("Shared LLM settings, instructions, and skills match both installations.")
            return int(bool(differences))
        actions = domain.plan_install(args.symlink) if args.command == "install" else domain.plan_backup()
        apply(REPO, actions, args.dry_run)
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
