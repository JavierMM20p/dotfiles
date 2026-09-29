"""Exercise the frontend-scratchpad script against temporary projects."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "scratchpad", ROOT / "llms/skills/frontend-scratchpad/scripts/scratchpad.py"
)
scratchpad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scratchpad)


def valid_spec():
    return {
        "html": '<main><div data-slot="hero"></div></main>',
        "vars": {"--a": "1"},
        "groups": [{"id": "g", "label": "G", "options": [
            {"id": "one", "label": "One", "vars": {"--a": "2"}},
            {"id": "two", "label": "Two", "slots": {"hero": "<h1>x</h1>"}, "js": "console.log('</script>')"},
        ]}],
    }


class ScratchpadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.enterContext(patch.object(scratchpad.tempfile, "gettempdir", return_value=str(self.root / "tmp")))
        self.enterContext(patch.dict(os.environ, {"FRONTEND_SCRATCHPAD_NO_OPEN": "1"}))

    def run_cli(self, *args):
        out = io.StringIO()
        with patch("sys.argv", ["scratchpad.py", *args]), contextlib.redirect_stdout(out):
            scratchpad.main()
        return out.getvalue()

    def prepare(self):
        project = self.root / "project"
        (project / "src/components").mkdir(parents=True)
        (project / "src/components/Button.tsx").write_text("export const Button = () => null")
        (project / "src/app.css").write_text(":root { --brand: #123456; }\nbody { font-family: Serif Face, serif; }")
        (project / "node_modules/x").mkdir(parents=True)
        (project / "node_modules/x/skip.css").write_text(":root { --hidden: 1; }")
        (project / "package.json").write_text(json.dumps({"dependencies": {"react": "^19"}}))
        output = self.run_cli("prepare", str(project), "--name", "Demo View")
        directory = Path(output.splitlines()[0].removeprefix("Scratchpad directory: "))
        return project, directory, output

    def test_prepare_summarizes_project_in_temp_directory(self):
        project, directory, output = self.prepare()
        self.assertTrue(directory.is_dir())
        self.assertTrue(directory.name.startswith("demo-view-"))
        self.assertEqual(json.loads((directory / "project.json").read_text())["root"], str(project))
        self.assertIn("react ^19", output)
        self.assertIn("--brand: #123456", output)
        self.assertIn("Serif Face, serif", output)
        self.assertIn("src/components/Button.tsx", output)
        self.assertNotIn("--hidden", output)

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_prepare_summarizes_compose_theme_and_composables(self):
        project = self.root / "android"
        self.write(project / "app/build.gradle.kts", "android { buildFeatures { compose = true } }\nimplementation(libs.androidx.material3)")
        self.write(project / "gradle/libs.versions.toml", 'composeBom = "2024.09.00"')
        self.write(project / "app/src/ui/theme/TidepoolTheme.kt", "\n".join([
            "val Tide500 = Color(0xFF1B6CA8)",
            "val Foam = Color(0x80FFFFFF)",
            "private val Light = lightColorScheme(primary = Tide500, onPrimary = Color(0xFFFFFFFF))",
            "val Title = TextStyle(fontFamily = GoogleFont(\"Inter\"), fontSize = 22.sp)",
            "val Sheet = RoundedCornerShape(topStart = 24.dp)",
        ]))
        self.write(project / "app/src/ui/eq/Equalizer.kt", "\n".join([
            "@OptIn(X::class)\n@Composable\nfun EqualizerSheet() {}",
            "@Composable\ninternal fun RowScope.BandSlider() {}",
            "@Composable\nprivate fun Helper() {}",
            "@Preview @Composable\nfun EqualizerSheetPreview() {}",
            "val Inline = Color(0xFF000000)",
        ]))
        output = self.run_cli("prepare", str(project))
        for expected in [
            "Jetpack Compose (BOM 2024.09.00) with Material 3", "Tide500: #1B6CA8", "Foam: #FFFFFF80",
            "lightColorScheme.primary: Tide500", "lightColorScheme.onPrimary: #FFFFFF",
            "Title: TextStyle(fontFamily = GoogleFont(\"Inter\"), fontSize = 22.sp)",
            "Sheet: RoundedCornerShape(topStart = 24.dp)", "Fonts: Inter",
            "app/src/ui/eq/Equalizer.kt: EqualizerSheet, BandSlider",
        ]:
            self.assertIn(expected, output)
        for unexpected in ["Helper", "EqualizerSheetPreview", "Inline"]:
            self.assertNotIn(unexpected, output)

    def test_prepare_recognizes_swiftui_and_flutter(self):
        ios = self.root / "ios"
        (ios / "App.xcodeproj").mkdir(parents=True)
        self.write(ios / "App/Player.swift", "import SwiftUI\nstruct PlayerView: View {}\nprivate struct Row: View {}")
        self.write(ios / "App/Assets.xcassets/Ocean.colorset/Contents.json", json.dumps({"colors": [
            {"color": {"components": {"red": "0x1B", "green": "108", "blue": "0.659"}}},
        ]}))
        output = self.run_cli("prepare", str(ios))
        for expected in ["Stack: SwiftUI", "Ocean: #1B6CA8", "App/Player.swift: PlayerView"]:
            self.assertIn(expected, output)
        self.assertNotIn("Row", output)

        flutter = self.root / "flutter"
        self.write(flutter / "pubspec.yaml", "dependencies:\n  flutter:\n    sdk: flutter\n")
        self.write(flutter / "android/build.gradle", "android {}")
        self.write(flutter / "lib/theme/colors.dart", "class C { static const ocean = Color(0xFF1B6CA8); }")
        self.write(flutter / "lib/eq.dart", "class EqualizerPanel extends StatelessWidget {}\nclass _Band extends StatefulWidget {}")
        output = self.run_cli("prepare", str(flutter))
        for expected in ["Stack: Flutter\n", "ocean: #1B6CA8", "lib/eq.dart: EqualizerPanel"]:
            self.assertIn(expected, output)
        self.assertNotIn("Gradle", output)
        self.assertNotIn("_Band", output)

    def test_build_embeds_spec_safely(self):
        project, directory, _ = self.prepare()
        (project / "src/fonts").mkdir()
        spec = valid_spec() | {"include": ["src/app.css"], "css": "main { background: url(bg.png); }"}
        (directory / "spec.json").write_text(json.dumps(spec))
        self.run_cli("build", str(directory))
        page = (directory / "index.html").read_text()
        self.assertNotIn("/*SPEC*/null", page)
        self.assertIn("--brand: #123456", page)
        self.assertIn("<\\/script>", page)
        self.assertNotIn("console.log('</script>')", page)

    def test_validation_reports_every_problem(self):
        spec = valid_spec()
        spec["groups"].append({"id": "Bad", "label": "B", "options": [{"id": "x", "label": "", "slots": {"nope": ""}, "color": 1}]})
        spec["groups"][0]["options"].append({"id": "three", "label": "Three", "vars": {"--a": "2"}})
        errors = "\n".join(scratchpad.validate(spec))
        for expected in ["lowercase", "at least 2", "unknown keys ['color']", "slot 'nope'", "label must be", "identical to option 'one'"]:
            self.assertIn(expected, errors)
        self.assertEqual(scratchpad.validate(valid_spec()), [])
        attribute_only = valid_spec()
        attribute_only["groups"][0]["options"] = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]
        self.assertEqual(scratchpad.validate(attribute_only), [])

    def test_build_reports_json_errors_at_end_of_file(self):
        _, directory, _ = self.prepare()
        (directory / "spec.json").write_text('{"html": "x",')
        with self.assertRaises(SystemExit) as raised:
            self.run_cli("build", str(directory))
        self.assertIn("line 1 column 14", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
