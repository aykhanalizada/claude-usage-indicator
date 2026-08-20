# Claude Usage Indicator

Claude Code usage indicator for Ubuntu/Fedora GNOME topbar.

Shows 5-hour usage percentage as a circular progress ring icon, updated every 2 minutes.

## Requirements

**Ubuntu:**
```bash
sudo apt install python3-gi python3-cairo gir1.2-ayatanaappindicator3-0.1
```

**Fedora:**
```bash
sudo dnf install python3-gobject python3-cairo libappindicator-gtk3
```

Also requires the **AppIndicator and KStatusNotifierItem Support** GNOME extension (pre-installed on Ubuntu, install from extensions.gnome.org on Fedora).

## Install

```bash
chmod +x install.sh
./install.sh
```

Then run:
```bash
claude-usage-indicator
```

## Notes

- Reads OAuth token from `~/.claude/.credentials.json` (set by Claude Code login)
- Caches API responses to avoid rate limits
- Token usage stats read from `~/.claude/projects/**/*.jsonl` (local, no network)
