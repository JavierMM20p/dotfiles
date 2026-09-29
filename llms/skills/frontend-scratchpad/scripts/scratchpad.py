#!/usr/bin/env python3
"""Prepare and build a temporary design scratchpad page from a JSON spec."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import webbrowser

SKILL = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL / "assets/scratchpad.html"
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "out", ".next", ".nuxt", ".svelte-kit", ".output",
    "coverage", "vendor", "target", ".venv", "venv", "__pycache__", ".turbo", ".cache",
}
STYLE_EXT = {".css", ".scss", ".sass", ".less"}
COMPONENT_EXT = {".tsx", ".jsx", ".vue", ".svelte", ".astro"}
MARKUP_EXT = STYLE_EXT | COMPONENT_EXT | {".html", ".ts", ".js"}
MAX_FILES = 4000
MAX_BYTES = 400_000
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SPEC_KEYS = {"title", "html", "css", "js", "head", "vars", "fonts", "include", "tailwind", "groups"}
GROUP_KEYS = {"id", "label", "options"}
OPTION_KEYS = {"id", "label", "vars", "css", "js", "head", "fonts", "slots", "shader"}
SHADER_KEYS = {"target", "frag", "uniforms"}


def walk(root):
    count = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            path = Path(base, name)
            if path.suffix in MARKUP_EXT:
                count += 1
                if count > MAX_FILES:
                    return
                yield path


def read(path):
    try:
        if path.stat().st_size > MAX_BYTES:
            return ""
        return path.read_text(errors="replace")
    except OSError:
        return ""


def stack(root):
    try:
        data = json.loads((root / "package.json").read_text())
    except (OSError, ValueError):
        return []
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    known = [
        "next", "react", "vue", "nuxt", "svelte", "@sveltejs/kit", "astro", "solid-js", "@angular/core",
        "vite", "tailwindcss", "@tailwindcss/vite", "styled-components", "@emotion/react", "sass",
        "@radix-ui/react-slot", "@mui/material", "@chakra-ui/react", "framer-motion", "motion", "three",
    ]
    return [f"{name} {deps[name]}" for name in known if name in deps]


def prepare(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.exit(f"error: project root not found: {root}")
    slug = re.sub(r"[^a-z0-9-]+", "-", (args.name or root.name).lower()).strip("-") or "scratchpad"
    out = Path(tempfile.gettempdir(), "frontend-scratchpad", f"{slug}-{time.strftime('%Y%m%d-%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "project.json").write_text(json.dumps({"root": str(root)}))

    variables, fonts, stylesheets, components = {}, [], [], []
    for path in walk(root):
        rel = path.relative_to(root).as_posix()
        text = read(path)
        if path.suffix in STYLE_EXT or path.suffix in {".vue", ".svelte", ".astro"}:
            found = re.findall(r"(--[\w-]+)\s*:\s*([^;{}]+);", text)
            if found and path.suffix in STYLE_EXT:
                stylesheets.append(f"{rel} ({len(found)} custom properties)")
            for name, value in found:
                variables.setdefault(name, " ".join(value.split())[:70])
            fonts += [" ".join(f.split())[:80] for f in re.findall(r"font-family\s*:\s*([^;{}]+)", text)]
        fonts += re.findall(r"fonts\.googleapis\.com/css2?\?family=([^\"'&)]+)", text)
        fonts += [f"next/font: {f.strip()}" for f in re.findall(r"import\s*{([^}]+)}\s*from\s*['\"]next/font/google", text)]
        if path.suffix in COMPONENT_EXT and ({"components", "ui"} & set(path.parts) or path.suffix in {".vue", ".svelte"}):
            components.append(rel)

    print(f"Scratchpad directory: {out}")
    print(f"Write the spec to: {out / 'spec.json'}")
    print(f"Project root: {root}")
    print("Stack: " + (", ".join(stack(root)) or "no package.json dependencies recognized"))
    configs = [p.name for p in root.glob("tailwind.config.*")]
    if configs:
        print("Tailwind config: " + ", ".join(configs))
    print("Stylesheets with custom properties: " + ("; ".join(stylesheets[:15]) or "none"))
    if variables:
        items = list(variables.items())
        print(f"Custom properties ({len(items)}, first 80):")
        for name, value in items[:80]:
            print(f"  {name}: {value}")
    unique_fonts = list(dict.fromkeys(fonts))
    print("Fonts: " + (" | ".join(unique_fonts[:15]) or "none found"))
    print(f"Components ({len(components)}, first 150):")
    for rel in components[:150]:
        print(f"  {rel}")


def check_str_map(value, where, errors, prefix=None):
    if not isinstance(value, dict):
        errors.append(f"{where} must be an object")
        return
    for key, item in value.items():
        if prefix and not key.startswith(prefix):
            errors.append(f"{where}: key {key!r} must start with {prefix!r}")
        if not isinstance(item, (str, int, float)):
            errors.append(f"{where}: value of {key!r} must be a string or number")


def check_list(value, where, errors):
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        errors.append(f"{where} must be a list of strings")


def check_keys(obj, allowed, where, errors):
    unknown = sorted(set(obj) - allowed)
    if unknown:
        errors.append(f"{where}: unknown keys {unknown}; allowed: {sorted(allowed)}")


def validate(spec):
    errors = []
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]
    check_keys(spec, SPEC_KEYS, "spec", errors)
    if not isinstance(spec.get("html"), str) or not spec["html"].strip():
        errors.append("spec.html must be a non-empty string")
    for key in ("title", "css", "js", "head"):
        if key in spec and not isinstance(spec[key], str):
            errors.append(f"spec.{key} must be a string")
    if "vars" in spec:
        check_str_map(spec["vars"], "spec.vars", errors, "--")
    for key in ("fonts", "include"):
        if key in spec:
            check_list(spec[key], f"spec.{key}", errors)
    if "tailwind" in spec and not isinstance(spec["tailwind"], bool):
        errors.append("spec.tailwind must be true or false")
    slots = set(re.findall(r"data-slot\s*=\s*[\"']([^\"']+)[\"']", spec.get("html") or ""))
    groups = spec.get("groups")
    if not isinstance(groups, list) or not groups:
        return errors + ["spec.groups must be a non-empty list"]
    group_ids = set()
    for gi, group in enumerate(groups):
        where = f"groups[{gi}]"
        if not isinstance(group, dict):
            errors.append(f"{where} must be an object")
            continue
        check_keys(group, GROUP_KEYS, where, errors)
        gid = group.get("id")
        if not isinstance(gid, str) or not SLUG.match(gid):
            errors.append(f"{where}.id must be lowercase letters, digits and hyphens")
        elif gid in group_ids:
            errors.append(f"{where}.id {gid!r} is duplicated")
        group_ids.add(gid)
        where = f"group {gid!r}"
        if not isinstance(group.get("label"), str):
            errors.append(f"{where}: label must be a string")
        options = group.get("options")
        if not isinstance(options, list):
            errors.append(f"{where}: options must be a list")
            continue
        if len(options) < 2:
            errors.append(f"{where}: needs at least 2 options")
        option_ids, bodies = set(), {}
        for oi, opt in enumerate(options):
            owhere = f"{where} options[{oi}]"
            if not isinstance(opt, dict):
                errors.append(f"{owhere} must be an object")
                continue
            check_keys(opt, OPTION_KEYS, owhere, errors)
            oid = opt.get("id")
            if not isinstance(oid, str) or not SLUG.match(oid):
                errors.append(f"{owhere}.id must be lowercase letters, digits and hyphens")
            elif oid in option_ids:
                errors.append(f"{owhere}.id {oid!r} is duplicated")
            option_ids.add(oid)
            owhere = f"{where} option {oid!r}"
            if not isinstance(opt.get("label"), str) or not opt["label"].strip():
                errors.append(f"{owhere}: label must be a non-empty string")
            for key in ("css", "js", "head"):
                if key in opt and not isinstance(opt[key], str):
                    errors.append(f"{owhere}: {key} must be a string")
            if "vars" in opt:
                check_str_map(opt["vars"], f"{owhere} vars", errors, "--")
            if "fonts" in opt:
                check_list(opt["fonts"], f"{owhere} fonts", errors)
            if "slots" in opt:
                check_str_map(opt["slots"], f"{owhere} slots", errors)
                if isinstance(opt["slots"], dict):
                    for name in sorted(set(opt["slots"]) - slots):
                        errors.append(f"{owhere}: slot {name!r} has no data-slot=\"{name}\" in spec.html; found {sorted(slots)}")
            if "shader" in opt:
                shaders = opt["shader"] if isinstance(opt["shader"], list) else [opt["shader"]]
                for shader in shaders:
                    if not isinstance(shader, dict) or not isinstance(shader.get("target"), str) or not isinstance(shader.get("frag"), str):
                        errors.append(f"{owhere}: shader needs string target and frag")
                        continue
                    check_keys(shader, SHADER_KEYS, f"{owhere} shader", errors)
                    if "uniforms" in shader:
                        check_list(shader["uniforms"], f"{owhere} shader.uniforms", errors)
            # Options without fields are styled through shared [data-<group>] selectors.
            body = json.dumps({k: v for k, v in opt.items() if k not in {"id", "label"}}, sort_keys=True)
            if body != "{}" and body in bodies:
                errors.append(f"{owhere} is identical to option {bodies[body]!r}")
            bodies.setdefault(body, oid)
    return errors


def inline_includes(spec, root):
    parts = []
    for rel in spec.get("include", []):
        path = (root / rel).resolve()
        try:
            text = path.read_text()
        except OSError as err:
            raise SystemExit(f"error: include {rel!r}: {err.strerror}")

        def absolute(match):
            url = match.group(2)
            if re.match(r"^(data:|https?:|file:|/|#)", url):
                return match.group(0)
            return f"url({match.group(1)}{(path.parent / url).resolve().as_uri()}{match.group(1)})"

        parts.append(f"/* {rel} */\n" + re.sub(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", absolute, text))
    return "\n".join(parts + [spec.get("css", "")])


def build(args):
    out = Path(args.dir).resolve()
    spec_path = out / "spec.json"
    try:
        spec = json.loads(spec_path.read_text())
    except OSError as err:
        sys.exit(f"error: cannot read {spec_path}: {err.strerror}")
    except json.JSONDecodeError as err:
        lines = err.doc.splitlines() or [""]
        line = lines[min(err.lineno, len(lines)) - 1]
        sys.exit(f"error: {spec_path} line {err.lineno} column {err.colno}: {err.msg}\n  {line[max(0, err.colno - 60):err.colno + 20]}")
    errors = validate(spec)
    if errors:
        sys.exit("error: invalid spec\n" + "\n".join(f"  - {e}" for e in errors))
    try:
        root = Path(json.loads((out / "project.json").read_text())["root"])
    except (OSError, ValueError, KeyError):
        root = Path.cwd()
    if spec.get("include"):
        spec = {**spec, "css": inline_includes(spec, root)}
    safe = lambda value: json.dumps(value, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    page = TEMPLATE.read_text().replace("/*SPEC*/null", safe(spec), 1).replace('/*SPEC_PATH*/""', safe(str(spec_path)), 1)
    index = out / "index.html"
    index.write_text(page)
    options = sum(len(g["options"]) for g in spec["groups"])
    print(f"Built {index} ({len(spec['groups'])} groups, {options} options, {len(page) // 1024} KiB)")
    if args.no_open or os.environ.get("FRONTEND_SCRATCHPAD_NO_OPEN"):
        print(f"Not opened; the user can open {index.as_uri()}")
    elif webbrowser.open(index.as_uri()):
        print("Opened in the browser.")
    else:
        print(f"Could not open a browser; the user can open {index.as_uri()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="create the scratchpad directory and summarize the project")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--name", help="short name for the directory")
    p.set_defaults(func=prepare)
    b = sub.add_parser("build", help="validate spec.json and write index.html")
    b.add_argument("dir")
    b.add_argument("--no-open", action="store_true", help="do not open the page in a browser")
    b.set_defaults(func=build)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
