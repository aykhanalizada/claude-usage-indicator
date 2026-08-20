#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DATA_DIR="$HOME/.local/share/claude-indicator/hicolor/22x22/apps"
AUTOSTART_DIR="$HOME/.config/autostart"
APP_DIR="$HOME/.local/share/applications"

# Dependencies check
echo "Checking dependencies..."
python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null || { echo "Missing: python3-gi"; exit 1; }
python3 -c "import cairo" 2>/dev/null || { echo "Missing: python3-cairo"; exit 1; }
python3 -c "
import gi
try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3
except:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
" 2>/dev/null || { echo "Missing: gir1.2-ayatanaappindicator3-0.1 (Ubuntu) or libappindicator-gtk3 (Fedora)"; exit 1; }

mkdir -p "$BIN_DIR" "$DATA_DIR" "$AUTOSTART_DIR" "$APP_DIR"

install -m 755 "$SCRIPT_DIR/claude-usage-indicator.py" "$BIN_DIR/claude-usage-indicator"

cat > "$AUTOSTART_DIR/claude-usage-indicator.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Claude Usage Indicator
Exec=$BIN_DIR/claude-usage-indicator
Icon=system-monitor
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Claude Code usage indicator for topbar
EOF

cat > "$APP_DIR/claude-usage-indicator.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Claude Usage Indicator
Exec=$BIN_DIR/claude-usage-indicator
Icon=system-monitor
Comment=Claude Code usage indicator for topbar
Categories=Utility;
EOF

echo "Done. Run: claude-usage-indicator"
