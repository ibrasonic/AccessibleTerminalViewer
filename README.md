# AccessibleTerminalViewer

AccessibleTerminalViewer is an NVDA add-on by Ibrahim Badawy for Command Prompt, PowerShell, and
Windows Terminal. Press **NVDA+Shift+V** while focused in a terminal to open a
structured browse-mode snapshot.

The add-on turns detected prompts into headings, common tabular output into
real HTML tables, and list-like output into lists. Unclassified content remains
preformatted, while blank-only terminal rows are removed.

The add-on is last tested with **NVDA 2026.3.1**.

Installing AccessibleTerminalViewer automatically schedules the obsolete
`terminalVirtualView` add-on for removal. Restart NVDA after installation so
only the current add-on handles NVDA+Shift+V.

## Updates

AccessibleTerminalViewer checks the latest public GitHub Release shortly after
NVDA starts. When a newer version is available, it offers to download, verify,
and install the `.nvda-addon` package. A manual **Check
AccessibleTerminalViewer for updates** command is available in NVDA's Input
Gestures dialog.

Release tags and the packaged manifest must use the same version, for example
`v1.0.0` and `version = 1.0.0`.

## Build

Run:

```powershell
.\build.ps1
```

The installable package is created in `dist`.

Pushing a tag such as `v1.0.0` runs the GitHub Actions workflow and publishes
the generated package as a GitHub Release asset.

## Test

Run:

```powershell
python -m unittest discover -s tests -v
```
