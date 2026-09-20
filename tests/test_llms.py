"""Exercise installation and export against isolated homes and repository copies."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("llms", ROOT / "scripts/llms.py")
llms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llms)


class LLMTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        shutil.copytree(ROOT / "llms", self.repo / "llms")
        self.home.mkdir()
        self.enterContext(patch.object(Path, "home", return_value=self.home))
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def domain(self):
        return llms.Domain(self.repo)

    def install(self, symlink=False):
        domain = self.domain()
        llms.apply(self.repo, domain.plan_install(symlink), False)
        return domain

    def test_merge_preserves_unmanaged_values_and_is_idempotent(self):
        codex = self.home / ".codex/config.toml"
        claude = self.home / ".claude/settings.json"
        self.write(codex, '# personal comment\nmodel = "old"\n[projects."/a.b/repo"]\ntrust_level = "trusted"\n[mcp_servers.demo]\nargs = ["a", "b"]\n')
        self.write(claude, json.dumps({"model": "old", "theme": "dark", "env": {"LOCAL_ONLY": "private"}}))
        codex.chmod(0o640)
        domain = self.install()
        data = tomllib.loads(codex.read_text())
        self.assertEqual(data["projects"]["/a.b/repo"]["trust_level"], "trusted")
        self.assertEqual(data["mcp_servers"]["demo"]["args"], ["a", "b"])
        self.assertEqual(json.loads(claude.read_text())["env"], {"LOCAL_ONLY": "private"})
        self.assertEqual(json.loads(claude.read_text())["attribution"], {"commit": "", "pr": "", "sessionUrl": False})
        self.assertEqual(codex.stat().st_mode & 0o777, 0o640)
        self.assertEqual(domain.differences(), [])
        self.assertEqual(domain.plan_install(False), [])
        self.assertEqual(domain.plan_backup(), [])
        self.assertNotIn("LOCAL_ONLY", (self.repo / "llms/settings.toml").read_text())
        backups = list(self.repo.glob(".config-backup-*/manifest.jsonl"))
        self.assertEqual(len(backups), 1)
        entries = [json.loads(line) for line in backups[0].read_text().splitlines()]
        originals = {entry["original"] for entry in entries}
        self.assertEqual(originals, {str(codex), str(claude)})
        self.assertTrue(any("personal comment" in (backups[0].parent / entry["backup"]).read_text() for entry in entries))

    def test_dry_run_changes_neither_home_nor_repo(self):
        before = llms.snapshot(self.root)
        llms.apply(self.repo, self.domain().plan_install(True), True)
        self.assertEqual(llms.snapshot(self.root), before)

    def test_symlinks_remove_other_skills_and_settings_are_regular(self):
        self.write(self.home / ".claude/skills/synced/keep.txt", "account skill")
        self.write(self.home / ".agents/skills/unrelated/SKILL.md", "other skill")
        domain = self.install(True)
        for source, targets in domain.content:
            for target in targets:
                self.assertTrue(target.is_symlink())
                self.assertEqual(target.resolve(), source.resolve())
        self.assertFalse((self.home / ".claude/skills/synced").exists())
        self.assertFalse((self.home / ".agents/skills/unrelated").exists())
        self.assertTrue(all(not path.is_symlink() for path in domain.settings.values()))
        self.assertEqual(domain.plan_install(True), [])
        self.assertEqual(domain.plan_backup(), [])
        llms.apply(self.repo, domain.plan_install(False), False)
        self.assertEqual(domain.differences(), [])
        self.assertTrue(all(not path.is_symlink() for _, targets in domain.content for path in targets))

    def test_extra_skills_are_reported_removed_and_backed_up(self):
        domain = self.install()
        extras = [
            self.home / ".agents/skills/unrelated",
            self.home / ".claude/skills/synced",
            self.home / ".codex/skills/legacy",
            self.home / ".codex/skills/c4-mermaid-diagrams",
        ]
        for extra in extras:
            self.write(extra / "SKILL.md", f"personal skill: {extra.name}")
        system = self.home / ".codex/skills/.system/builtin/SKILL.md"
        self.write(system, "bundled skill")
        external = self.root / "external"
        self.write(external / "SKILL.md", "external skill")
        linked = self.home / ".agents/skills/linked"
        linked.symlink_to(external, target_is_directory=True)
        broken = self.home / ".claude/skills/broken"
        broken.symlink_to(self.root / "missing")
        extras.extend([linked, broken])
        differences = domain.differences()
        self.assertEqual(len(differences), len(extras))
        for extra in extras:
            self.assertTrue(any(str(extra) in item for item in differences))
        actions = domain.plan_install(False)
        llms.apply(self.repo, actions, True)
        self.assertTrue(all(path.exists() or path.is_symlink() for path in extras))
        self.assertEqual(list(self.repo.glob(".config-backup-*")), [])
        llms.apply(self.repo, actions, False)
        self.assertTrue(all(not path.exists() and not path.is_symlink() for path in extras))
        self.assertEqual(system.read_text(), "bundled skill")
        self.assertEqual((external / "SKILL.md").read_text(), "external skill")
        manifests = list(self.repo.glob(".config-backup-*/manifest.jsonl"))
        self.assertEqual(len(manifests), 1)
        entries = [json.loads(line) for line in manifests[0].read_text().splitlines()]
        self.assertEqual({entry["original"] for entry in entries}, {str(path) for path in extras})
        for entry in entries:
            saved = manifests[0].parent / entry["backup"]
            if entry["original"] in {str(linked), str(broken)}:
                self.assertTrue(saved.is_symlink())
            else:
                self.assertEqual((saved / "SKILL.md").read_text(), f"personal skill: {Path(entry['original']).name}")
        self.assertEqual(domain.differences(), [])
        self.assertEqual(domain.plan_install(False), [])

    def test_removed_source_skill_is_pruned_in_copy_and_symlink_modes(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                source = self.repo / "llms/skills/temporary"
                self.write(source / "SKILL.md", "temporary skill")
                self.install(symlink)
                shutil.rmtree(source)
                domain = self.domain()
                self.assertEqual(len(domain.differences()), 2)
                self.install(symlink)
                for root in domain.skill_roots:
                    self.assertFalse((root / "temporary").exists())
                    self.assertFalse((root / "temporary").is_symlink())
                self.assertEqual(domain.differences(), [])

    def test_empty_source_removes_all_personal_skills(self):
        self.install()
        shutil.rmtree(self.repo / "llms/skills/c4-mermaid-diagrams")
        domain = self.install()
        self.assertTrue(all(list(root.iterdir()) == [] for root in domain.skill_roots))
        self.assertEqual(domain.differences(), [])

    def test_skill_cleanup_respects_custom_configuration_directories(self):
        codex = self.home / "custom-codex"
        claude = self.home / "custom-claude"
        with patch.dict(os.environ, {"CODEX_HOME": str(codex), "CLAUDE_CONFIG_DIR": str(claude)}):
            self.write(codex / "skills/extra/SKILL.md", "extra")
            self.write(claude / "skills/extra/SKILL.md", "extra")
            self.write(self.home / ".claude/skills/untouched/SKILL.md", "other configuration")
            domain = self.install()
            self.assertFalse((codex / "skills/extra").exists())
            self.assertFalse((claude / "skills/extra").exists())
            self.assertTrue((claude / "skills/c4-mermaid-diagrams/SKILL.md").is_file())
            self.assertTrue((self.home / ".claude/skills/untouched/SKILL.md").is_file())
            self.assertEqual(domain.differences(), [])

    def test_skill_root_symlink_fails_before_changes(self):
        external = self.root / "external"
        self.write(external / "extra/SKILL.md", "external skill")
        root = self.home / ".agents/skills"
        root.parent.mkdir()
        root.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            self.domain().plan_install(False)
        self.assertEqual((external / "extra/SKILL.md").read_text(), "external skill")
        self.assertFalse((self.home / ".codex/config.toml").exists())

    def test_backup_conflict_prevents_all_exports(self):
        domain = self.install()
        self.write(domain.settings["codex"], 'model = "new-model"\nmodel_reasoning_effort = "high"\n')
        self.write(self.home / ".claude/CLAUDE.md", "different instructions")
        before = llms.snapshot(self.repo / "llms")
        with self.assertRaisesRegex(ValueError, "conflicting copies"):
            domain.plan_backup()
        self.assertEqual(llms.snapshot(self.repo / "llms"), before)

    def test_backup_exports_only_managed_values_and_agreed_content(self):
        domain = self.install()
        self.write(domain.settings["codex"], 'model = "new-model"\nmodel_reasoning_effort = "medium"\nsecret = "stay local"\n')
        claude = json.loads(domain.settings["claude"].read_text())
        claude.update({"model": "opus", "effortLevel": "medium", "env": {"TOKEN": "stay local"}})
        self.write(domain.settings["claude"], json.dumps(claude))
        for _, targets in domain.content:
            for target in targets:
                if target.is_file():
                    target.write_text("Updated shared instructions\n")
                else:
                    (target / "helper.sh").write_text("#!/bin/sh\nexit 0\n")
                    (target / "helper.sh").chmod(0o755)
        llms.apply(self.repo, domain.plan_backup(), False)
        self.assertEqual(self.domain().differences(), [])
        text = (self.repo / "llms/settings.toml").read_text()
        self.assertNotIn("stay local", text)
        self.assertIn('reasoning_effort = "medium"', text)
        self.assertIn('model = "new-model"', text)
        self.assertTrue((self.repo / "llms/skills/c4-mermaid-diagrams/helper.sh").stat().st_mode & 0o111)

    def test_effort_conflicts_and_missing_files_fail_backup(self):
        domain = self.install()
        self.write(domain.settings["claude"], '{"model":"opus","effortLevel":"low"}')
        with self.assertRaisesRegex(ValueError, "reasoning effort"):
            domain.plan_backup()
        self.install()
        (self.home / ".codex/AGENTS.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            domain.plan_backup()

    def test_check_detects_setting_content_and_shadowing(self):
        domain = self.install()
        self.write(domain.settings["claude"], '{"model":"opus","effortLevel":"low"}')
        self.write(domain.override, "Override")
        (self.home / ".agents/skills/c4-mermaid-diagrams/SKILL.md").write_text("changed")
        differences = domain.differences()
        self.assertTrue(any("effortLevel" in item for item in differences))
        self.assertTrue(any("c4-mermaid-diagrams" in item for item in differences))
        self.assertTrue(any("shadows" in item for item in differences))

    def test_nested_settings_merge_and_conflict_preflight(self):
        settings = self.repo / "llms/settings.toml"
        settings.write_text(settings.read_text() + '\n[claude.permissions]\ndefaultMode = "default"\n')
        target = self.home / ".claude/settings.json"
        self.write(target, '{"permissions":{"allow":["Bash(git status)"]}}')
        domain = self.install()
        permissions = json.loads(target.read_text())["permissions"]
        self.assertEqual(permissions, {"allow": ["Bash(git status)"], "defaultMode": "default"})
        self.write(target, '{"permissions":"invalid"}')
        before = llms.snapshot(self.root)
        with self.assertRaisesRegex(ValueError, "existing scalar"):
            domain.plan_install(False)
        self.assertEqual(llms.snapshot(self.root), before)

    def test_broken_settings_and_nested_skill_symlinks_fail_before_writes(self):
        self.write(self.home / ".claude/settings.json", "{broken")
        before = llms.snapshot(self.root)
        with self.assertRaises(ValueError):
            self.domain().plan_install(False)
        self.assertEqual(llms.snapshot(self.root), before)
        skill = self.repo / "llms/skills/c4-mermaid-diagrams"
        (skill / "outside").symlink_to(self.home)
        with self.assertRaisesRegex(ValueError, "nested symlinks"):
            self.domain()

    def test_existing_settings_symlink_does_not_mutate_its_source(self):
        original = self.root / "personal.toml"
        original.write_text('model = "old"\n')
        target = self.home / ".codex/config.toml"
        target.parent.mkdir(parents=True)
        target.symlink_to(original)
        self.install(True)
        self.assertFalse(target.is_symlink())
        self.assertEqual(original.read_text(), 'model = "old"\n')

    def test_toml_roundtrip_retains_nontrivial_local_values(self):
        original = tomllib.loads('''
title = "Unicode: 日本語"
date = 2026-09-20
time = 07:32:00.123
timestamp = 2026-09-20T07:32:00Z
infinity = inf
"quoted.key" = { "a b" = true }
[[servers]]
name = "one"
[servers.nested]
ports = [1, 2]
[[servers]]
name = "two"
''')
        self.assertEqual(tomllib.loads(llms.dump_toml(original)), original)

    def test_cli_exit_codes_and_dry_run(self):
        with patch.object(llms, "REPO", self.repo):
            with patch("sys.argv", ["llms.py", "check"]):
                self.assertEqual(llms.main(), 1)
            before = llms.snapshot(self.root)
            with patch("sys.argv", ["llms.py", "install", "--dry-run", "--symlink"]):
                self.assertEqual(llms.main(), 0)
            self.assertEqual(llms.snapshot(self.root), before)
            with patch("sys.argv", ["llms.py", "install", "--symlink"]):
                self.assertEqual(llms.main(), 0)
            with patch("sys.argv", ["llms.py", "check"]):
                self.assertEqual(llms.main(), 0)
            with patch("sys.argv", ["llms.py", "backup"]):
                self.assertEqual(llms.main(), 0)

    def test_native_backup_conflict_cannot_leak_new_settings(self):
        domain = self.install()
        claude = json.loads(domain.settings["claude"].read_text())
        claude["model"] = None
        self.write(domain.settings["claude"], json.dumps(claude))
        before = llms.snapshot(self.repo / "llms")
        with self.assertRaisesRegex(ValueError, "unsupported TOML"):
            domain.plan_backup()
        self.assertEqual(llms.snapshot(self.repo / "llms"), before)


if __name__ == "__main__":
    unittest.main()
