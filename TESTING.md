# Test status

Local automated validation: macOS 26.6, Python 3.14.6, September 7, 2026.

The test suite builds a real Swift helper and ad-hoc signed launcher around a synthetic signed app. It exercises build-change refresh, preserved profile data, collision refusal, process matching and focus behavior. It does not start or stop Claude or edit the Dock.

## Manual release check still required

1. Finish running work. Create a disposable profile with a new name.
2. Pin its launcher and check the colored launcher and running-app icons.
3. Close other Desktop instances yourself, sign into the intended test account, and confirm its identity.
4. Reopen another profile and check separate account identities while both run.
5. Launch the same profile again and confirm it focuses the existing window.
6. Quit the test profile, move its launcher and tool-owned folder to Trash, and separately decide whether to keep or remove its profile data.

The underlying approach worked in the maintainer's earlier setup. Those observations are not a complete end-to-end test of this rewritten release. Compatibility is experimental until this checklist is completed for the release and app version.
