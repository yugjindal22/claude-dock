# Details

`create` builds a launcher and a tiny Swift helper locally. Icons are colored tiles with initials, drawn from scratch. No Claude artwork or app binaries are shipped in this repository.

The launcher opens a copy of the user's installed Claude Desktop with `--user-data-dir` pointing at its own profile folder. The copy keeps Anthropic's bundle identifier and signature. A Finder custom icon changes its appearance; strict signature validation may report Finder metadata, while normal deep signature verification remains applicable. The launcher itself is locally ad-hoc signed, not notarized by Apple.

Locations for a profile named `two`:

| Item | Location under your home folder |
| --- | --- |
| Launcher | `Applications/Claude Two.app` |
| Desktop profile | `Library/Application Support/Claude-Two` |
| Helper, app copy, configuration | `Library/Application Support/claude-dock/two` |

The launcher records the Python executable used at installation. If Python moves or is removed, the launcher needs repair. Source app refreshes compare both the version plist and signature resources, stage the replacement first, and preserve profile data. A running profile is focused, never replaced. Creation refuses collisions, including profiles made by another tool.

This isolates Desktop browser storage, not the whole OS environment. Global `~/.claude` settings and CLI history are not copied or changed. Reusing an existing project means sharing its files. Cloud chats belong to the account you log into. OS permissions and Keychain integration can overlap. MCP and browser integrations need their own testing.

Electron exposes user-data storage, but individual apps can override it or share authentication elsewhere. This repo only targets Claude Desktop. Other apps need separate investigation; do not assume Codex or another Electron app is compatible.

## Testing

```sh
python3 -m unittest discover -s tests -v
```

The native smoke test compiles the real Swift helper, draws icons, builds signed launchers and refreshes a signed synthetic app in a temporary folder. It launches no Claude process, changes no Dock preferences, and cleans up its fixtures. Unit tests cover name validation, collisions, process matching and focusing an existing instance.

The earlier profile technique was manually exercised with real accounts. This rewritten utility has automated fixture coverage; a fresh-account login and full UI test of this version remain a manual release check. See [TESTING.md](TESTING.md). Neither a passing test nor a signature check proves account-policy approval.

## Removing a profile

Quit that profile yourself. Move its launcher and its `claude-dock/<name>` directory to Trash using Finder. Keep the `Claude-<Name>` profile folder if you want to retain its login and local data. Deleting that data is a separate, deliberate choice. Never remove the original `Claude` folder.
