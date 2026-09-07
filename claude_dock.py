#!/usr/bin/env python3
"""Small, local-only Claude Desktop profile launchers for macOS."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

COLORS = {"blue", "purple", "green", "orange", "pink", "teal"}


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def identity(name):
    if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", name) or len(name) > 40:
        raise ValueError("Use a short name such as two, three, or work-account.")
    slug = name.lower()
    if slug in {"default", "primary"}:
        raise ValueError("Choose a name other than default or primary.")
    return slug, " ".join(p.capitalize() for p in slug.split("-"))


def paths(home, name):
    slug, display = identity(name)
    support = home / "Library/Application Support"
    root = support / "claude-dock" / slug
    return {"root": root, "data": support / ("Claude-" + display),
            "launcher": home / "Applications" / ("Claude " + display + ".app"),
            "clone": root / ("Claude " + display + ".app"), "slug": slug, "display": display}


def processes():
    return run("/bin/ps", "-axo", "pid=,command=", capture_output=True, text=True).stdout.splitlines()


def profile_pid(data, lines=None):
    for line in processes() if lines is None else lines:
        match = re.match(r"\s*(\d+)\s+(.+)", line)
        if not match:
            continue
        command = match[2]
        if "/Contents/MacOS/Claude" not in command or "Helper" in command:
            continue
        # Match the complete path, not a prefix of another profile's name.
        flag = "--user-data-dir=" + str(data)
        if command.endswith(flag) or flag + " --" in command:
            return int(match[1])
    return None


def fingerprint(app):
    with (app / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    if info.get("CFBundleIdentifier") != "com.anthropic.claudefordesktop":
        raise ValueError("The source must be the official Claude Desktop app.")
    digest = hashlib.sha256((app / "Contents/Info.plist").read_bytes()).hexdigest()
    signature = app / "Contents/_CodeSignature/CodeResources"
    if signature.is_file():
        digest += hashlib.sha256(signature.read_bytes()).hexdigest()
    return digest


@contextlib.contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def helper(root):
    binary = root / "native"
    if not binary.exists():
        raise ValueError("Native helper missing. Reinstall from the repository.")
    return binary


def refresh(app, p, color):
    """Stage a signed copy before replacing only this tool's idle clone."""
    source_version = fingerprint(app)
    stamp = p["root"] / "source-fingerprint"
    if p["clone"].exists() and stamp.exists() and stamp.read_text() == source_version:
        return
    if profile_pid(p["data"]):
        raise ValueError("This profile is running. Quit it yourself before refreshing.")
    run("/usr/bin/codesign", "--verify", "--deep", app, capture_output=True)
    with tempfile.TemporaryDirectory(prefix="refresh-", dir=p["root"]) as temp:
        staged = Path(temp) / p["clone"].name
        result = subprocess.run(["/bin/cp", "-cR", str(app), str(staged)], capture_output=True)
        if result.returncode:
            if staged.exists():
                shutil.rmtree(staged)
            run("/usr/bin/ditto", app, staged)
        run("/usr/bin/codesign", "--verify", "--deep", staged, capture_output=True)
        if fingerprint(app) != source_version:
            raise ValueError("Claude updated during the copy. Try again when the update finishes.")
        run(helper(p["root"]), "seticon", p["root"] / "profile.icns", staged)
        previous = Path(temp) / "previous.app"
        if p["clone"].exists():
            p["clone"].rename(previous)
        try:
            staged.rename(p["clone"])
        except BaseException:
            if previous.exists():
                previous.rename(p["clone"])
            raise
        stamp.write_text(source_version)


def create(home, name, color, source):
    if sys.platform != "darwin":
        raise ValueError("This tool requires macOS.")
    if color not in COLORS:
        raise ValueError("Unknown color.")
    p = paths(home, name)
    # Existing profiles from any tool are never adopted or overwritten implicitly.
    if any(p[key].exists() for key in ("root", "data", "launcher")):
        raise ValueError("That profile or launcher already exists. Choose a new name.")
    fingerprint(source)
    if not shutil.which("swiftc"):
        raise ValueError("Install Xcode Command Line Tools with xcode-select --install first.")
    created = []
    try:
        p["root"].mkdir(parents=True, exist_ok=False)
        created.append(p["root"])
        os.chmod(p["root"], 0o700)
        native_source = Path(__file__).resolve().parent / "native.swift"
        run("/usr/bin/swiftc", "-O", native_source, "-o", p["root"] / "native")
        run(helper(p["root"]), "icon", color, p["display"][:2].upper(), p["root"] / "profile.icns")
        p["data"].mkdir(mode=0o700, exist_ok=False)
        created.append(p["data"])
        config = {"name": p["slug"], "color": color, "source": str(source), "home": str(home)}
        (p["root"] / "profile.json").write_text(json.dumps(config, indent=2))
        shutil.copy2(__file__, p["root"] / "claude_dock.py")
        with locked(p["root"]):
            refresh(source, p, color)
        p["launcher"].mkdir(parents=True, exist_ok=False)
        created.append(p["launcher"])
        contents = p["launcher"] / "Contents"
        (contents / "MacOS").mkdir(parents=True)
        (contents / "Resources").mkdir()
        # The Python executable is recorded at install time, avoiding Finder's PATH.
        executable = contents / "MacOS/launch"
        command = [sys.executable, str(p["root"] / "claude_dock.py"), "launch", p["slug"], "--home", str(home)]
        executable.write_text("#!/bin/sh\nexec " + shlex.join(command) + "\n")
        executable.chmod(0o755)
        shutil.copy2(p["root"] / "profile.icns", contents / "Resources/profile.icns")
        with (contents / "Info.plist").open("wb") as stream:
            plistlib.dump({"CFBundleIdentifier": "io.github.yugjindal22.claude-dock." + p["slug"],
                          "CFBundleName": "Claude " + p["display"], "CFBundleExecutable": "launch",
                          "CFBundlePackageType": "APPL", "CFBundleIconFile": "profile.icns",
                          "CFBundleShortVersionString": "0.1.0"}, stream)
        run("/usr/bin/codesign", "--force", "--sign", "-", p["launcher"], capture_output=True)
    except BaseException:
        for path in reversed(created):
            shutil.rmtree(path)
        raise
    print("Created " + str(p["launcher"]))
    print("Drag that app into the Dock. Run: python3 claude_dock.py launch " + p["slug"])
    print("Before its first login, finish your work and quit other Claude Desktop windows yourself.")
    return p


def launch(home, name):
    p = paths(home, name)
    if not (p["root"] / "profile.json").is_file():
        raise ValueError("Profile not found. Run create first.")
    if not p["data"].is_dir():
        raise ValueError("Profile data folder is missing. Restore it before launching.")
    with locked(p["root"]):
        config_path = p["root"] / "profile.json"
        if not config_path.exists():
            raise ValueError("Profile not found. Run create first.")
        pid = profile_pid(p["data"])
        if pid:
            run(helper(p["root"]), "focus", pid)
            return
        config = json.loads(config_path.read_text())
        refresh(Path(config["source"]), p, config["color"])
        # No keychain changes, app bundle ID changes, or login URL handlers.
        run("/usr/bin/open", "-n", p["clone"], "--args", "--user-data-dir=" + str(p["data"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create", help="Create a colored launcher without starting or quitting Claude")
    create_parser.add_argument("name")
    create_parser.add_argument("--color", choices=sorted(COLORS), default="blue")
    create_parser.add_argument("--app", type=Path, default=Path("/Applications/Claude.app"))
    launch_parser = sub.add_parser("launch", help="Launch or focus a profile")
    launch_parser.add_argument("name")
    list_parser = sub.add_parser("list", help="List profiles created by this tool")
    for item in (create_parser, launch_parser, list_parser):
        item.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    if args.command == "create":
        create(home, args.name, args.color, args.app.expanduser().resolve())
    elif args.command == "launch":
        launch(home, args.name)
    else:
        for config in sorted((home / "Library/Application Support/claude-dock").glob("*/profile.json")):
            data = json.loads(config.read_text())
            print(data["name"] + " (" + data["color"] + ")")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("Error: " + str(error), file=sys.stderr)
        sys.exit(1)
