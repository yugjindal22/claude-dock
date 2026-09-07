# Claude Dock

Claude Two. Claude Three. Separate logins. Different colors in your Mac's Dock.

A small utility for **Claude Desktop, including its Code tab**. Create a profile, sign in once, then open it alongside your other accounts. No dashboard or background service.

## Setup

**Easiest:** copy [this prompt](PROMPT.md) into a local coding assistant and let it handle setup.

Or use Terminal. Requires macOS, Claude Desktop, Python 3.9+, and Xcode Command Line Tools (`xcode-select --install`).

```sh
git clone https://github.com/yugjindal22/claude-dock.git
cd claude-dock
python3 claude_dock.py create two --color blue
python3 claude_dock.py create three --color purple
```

Drag `Claude Two.app` and `Claude Three.app` from your user's `Applications` folder into the Dock. Open either to sign in. Or run `python3 claude_dock.py launch two`.

Creating launchers can happen while Claude runs. **Before a new profile's first login, finish your tasks and quit the other Desktop instances yourself.** Login callbacks can otherwise reach the wrong window. This tool never quits apps or signs you out.

## What is separate?

Each launcher uses its own `--user-data-dir` and a local copy of your installed app. Desktop login and profile storage are separate. `~/.claude`, project files, Keychain and OS integrations are **not a security boundary** and can be shared. Avoid simultaneous edits to the same files.

Clones refresh from the installed app when its build changes. Updates can still break compatibility. This is an experimental macOS utility, not a universal Electron app cloner.

Want independent copies of your local Code chats too? [Claude Chat Copy](https://github.com/yugjindal22/claude-chat-copy).

[How it works and testing](DETAILS.md) · [MIT license](LICENSE) · [Credits](NOTICE.md) · [Use and contact](USE.md)
