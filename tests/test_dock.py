import importlib.util
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dock", ROOT / "claude_dock.py")
dock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dock)


class UnitTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(dock.identity("Work-Account"), ("work-account", "Work Account"))
        for name in ["../primary", "", "$(touch hacked)", "two;exit", "a/b", "default", "primary", "x" * 41]:
            with self.assertRaises(ValueError):
                dock.identity(name)

    def test_process_matching(self):
        data = Path("/Users/Test Person/Library/Application Support/Claude-Two")
        base = "111 /Apps/Claude Two.app/Contents/MacOS/Claude --user-data-dir="
        self.assertEqual(dock.profile_pid(data, [base + str(data)]), 111)
        self.assertIsNone(dock.profile_pid(data, [base + str(data) + " More"]))
        self.assertIsNone(dock.profile_pid(data, ["222 /Apps/Claude.app/Contents/MacOS/Claude"]))

    def test_existing_profile_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            p = dock.paths(home, "two")
            p["data"].mkdir(parents=True)
            sentinel = p["data"] / "do-not-touch"
            sentinel.write_text("keep")
            with patch.object(sys, "platform", "darwin"), self.assertRaises(ValueError):
                dock.create(home, "two", "blue", Path("/missing"))
            self.assertEqual(sentinel.read_text(), "keep")

    def test_refresh_refuses_running_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            p = dock.paths(Path(temp), "two")
            with patch.object(dock, "fingerprint", return_value="new"), patch.object(dock, "profile_pid", return_value=1):
                with self.assertRaises(ValueError):
                    dock.refresh(Path("/fake"), p, "blue")

    def test_focus_does_not_refresh_or_relaunch(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            p = dock.paths(home, "two")
            p["root"].mkdir(parents=True)
            (p["root"] / "profile.json").write_text("{}")
            (p["root"] / "native").touch()
            with patch.object(dock, "profile_pid", return_value=123), patch.object(dock, "refresh") as refresh, patch.object(dock, "run") as run:
                dock.launch(home, "two")
                refresh.assert_not_called()
                self.assertEqual(run.call_args.args[1:], ("focus", 123))


@unittest.skipUnless(sys.platform == "darwin", "native build smoke test requires macOS")
class NativeSmokeTests(unittest.TestCase):
    def test_create_refresh_and_integrity_without_launching(self):
        # An ad-hoc signed fixture containing /usr/bin/true, never the user's app.
        import shutil
        with tempfile.TemporaryDirectory(prefix="claude-dock-test-") as temp:
            home = Path(temp) / "Home With Spaces"
            source = Path(temp) / "Fixture Claude.app"
            (source / "Contents/MacOS").mkdir(parents=True)
            (source / "Contents/Resources").mkdir()
            shutil.copyfile("/usr/bin/true", source / "Contents/MacOS/Claude")
            (source / "Contents/MacOS/Claude").chmod(0o755)
            info = {"CFBundleIdentifier": "com.anthropic.claudefordesktop", "CFBundleExecutable": "Claude",
                    "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "1.0", "CFBundleVersion": "1"}
            def sign():
                with (source / "Contents/Info.plist").open("wb") as stream:
                    plistlib.dump(info, stream)
                subprocess.run(["codesign", "--force", "--sign", "-", str(source)], check=True, capture_output=True)
            sign()
            original = dock.fingerprint(source)
            p = dock.create(home, "test", "purple", source)
            self.assertTrue(p["launcher"].is_dir())
            self.assertEqual(dock.fingerprint(source), original)
            subprocess.run(["codesign", "--verify", "--deep", str(p["clone"])], check=True)
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(p["launcher"])], check=True)
            launcher = (p["launcher"] / "Contents/MacOS/launch").read_text()
            self.assertIn("'", launcher)  # Space-containing paths are shell quoted.
            (p["data"] / "login-sentinel").write_text("keep")
            info["CFBundleVersion"] = "2"  # Same marketing version, new build.
            sign()
            dock.refresh(source, p, "purple")
            self.assertNotEqual(dock.fingerprint(source), original)
            self.assertEqual(dock.fingerprint(source), dock.fingerprint(p["clone"]))
            self.assertEqual((p["data"] / "login-sentinel").read_text(), "keep")
            self.assertTrue((p["root"] / "profile.icns").stat().st_size > 100)


if __name__ == "__main__":
    unittest.main()
