#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except (ValueError, ImportError):
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as AppIndicator
import cairo
from gi.repository import Gtk, GLib

import json, os, math, glob, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

ICON_THEME_DIR = os.path.expanduser('~/.local/share/claude-indicator')
ICON_DIR       = os.path.join(ICON_THEME_DIR, 'hicolor', '22x22', 'apps')
CACHE_FILE     = os.path.join(ICON_THEME_DIR, 'cache.json')
os.makedirs(ICON_DIR, exist_ok=True)

# ── Cache ──────────────────────────────────────────────────────────────────────

def load_cache():
    try:
        with open(CACHE_FILE) as f:
            obj = json.load(f)
        if isinstance(obj, dict) and 'data' in obj:
            return obj['data'], obj.get('saved_at')
        return obj, None  # köhnə format
    except Exception:
        return None, None

def save_cache(data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'data': data, 'saved_at': datetime.now(timezone.utc).isoformat()}, f)
    except Exception:
        pass

# ── API ────────────────────────────────────────────────────────────────────────

def get_token():
    with open(os.path.expanduser('~/.claude/.credentials.json')) as f:
        return json.load(f)['claudeAiOauth']['accessToken']

def fetch_usage():
    token = get_token()
    req = urllib.request.Request("https://api.anthropic.com/api/oauth/usage")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("anthropic-beta", "oauth-2025-04-20")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    save_cache(data)
    return data

# ── Icon (Cairo PNG) ───────────────────────────────────────────────────────────

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def pct_color(pct):
    if pct < 50:   return '#4CAF50'
    elif pct < 75: return '#FF9800'
    elif pct < 90: return '#FF5722'
    else:          return '#F44336'

def make_icon(pct):
    path = os.path.join(ICON_DIR, f'claude-usage-{pct}.png')
    if os.path.exists(path):
        return path

    h = 22
    ring_w = 22
    pad = 3
    text = f"{pct}%"

    # Measure text width
    tmp = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
    tctx = cairo.Context(tmp)
    tctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    tctx.set_font_size(11)
    te = tctx.text_extents(text)
    text_w = int(te.width) + 2

    width = ring_w + pad + text_w
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, h)
    ctx = cairo.Context(surface)

    # Ring
    cx = cy = ring_w / 2
    r = 8.5
    ctx.set_source_rgba(0.33, 0.33, 0.33, 0.6)
    ctx.set_line_width(2.5)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.stroke()

    if pct > 0:
        rgb = hex_to_rgb(pct_color(pct))
        ctx.set_source_rgba(*rgb, 1.0)
        ctx.set_line_width(2.5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        start = -math.pi / 2
        ctx.arc(cx, cy, r, start, start + 2 * math.pi * pct / 100)
        ctx.stroke()

    # Text
    rgb = hex_to_rgb(pct_color(pct)) if pct > 0 else (0.7, 0.7, 0.7)
    ctx.set_source_rgba(*rgb, 1.0)
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(11)
    te2 = ctx.text_extents(text)
    tx = ring_w + pad - te2.x_bearing
    ty = (h - te2.height) / 2 - te2.y_bearing
    ctx.move_to(tx, ty)
    ctx.show_text(text)

    surface.write_to_png(path)
    return path

# ── Tokens (JSONL) ─────────────────────────────────────────────────────────────

def fetch_tokens():
    sessions_dir = os.path.expanduser('~/.claude/projects')
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=5)
    total = 0
    for filepath in glob.glob(os.path.join(sessions_dir, '**/*.jsonl'), recursive=True):
        try:
            with open(filepath) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        ts = data.get('timestamp', '')
                        if not ts:
                            continue
                        if datetime.fromisoformat(ts.replace('Z', '+00:00')) < window_start:
                            continue
                        msg = data.get('message', {})
                        u = msg.get('usage', {}) if isinstance(msg, dict) else {}
                        if u:
                            total += u.get('input_tokens', 0) + u.get('output_tokens', 0) + u.get('cache_creation_input_tokens', 0)
                    except Exception:
                        pass
        except Exception:
            pass
    return total

def fmt_tokens(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}k"
    return str(n)

def fmt_reset(iso_str):
    if not iso_str:
        return ""
    return datetime.fromisoformat(iso_str).astimezone().strftime('%H:%M')

def fmt_reset_weekly(iso_str):
    if not iso_str:
        return ""
    days = ['B.e', 'Ç.a', 'Çər', 'C.a', 'Cüm', 'Şnb', 'Baz']
    dt = datetime.fromisoformat(iso_str).astimezone()
    return f"{days[dt.weekday()]} {dt.strftime('%d %H:%M')}"

# ── Indicator ──────────────────────────────────────────────────────────────────

class ClaudeIndicator:
    def __init__(self):
        self.indicator = AppIndicator.Indicator.new(
            "claude-usage",
            "dialog-information",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()

        self.session_item = Gtk.MenuItem(label="Yüklənir...")
        self.session_item.set_sensitive(False)
        self.menu.append(self.session_item)

        self.weekly_item = Gtk.MenuItem(label="")
        self.weekly_item.set_sensitive(False)
        self.menu.append(self.weekly_item)

        self.token_item = Gtk.MenuItem(label="")
        self.token_item.set_sensitive(False)
        self.menu.append(self.token_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        refresh_item = Gtk.MenuItem(label="↻  Yenilə")
        refresh_item.connect("activate", lambda _: self._manual_refresh())
        self.menu.append(refresh_item)

        quit_item = Gtk.MenuItem(label="✕  Çıx")
        quit_item.connect("activate", lambda _: Gtk.main_quit())
        self.menu.append(quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        self._next_interval = 120
        self._last_pct = None  # son uğurlu faizi saxla

        # Başlanğıcda keşdən oxu — API-yə getmə
        cached, saved_at = load_cache()
        if cached:
            self._apply(cached)
            wait = self._next_interval
            if saved_at:
                try:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(saved_at)).total_seconds()
                    wait = max(15, int(self._next_interval - age))
                except Exception:
                    pass
            GLib.timeout_add_seconds(wait, self._first_update)
        else:
            GLib.timeout_add_seconds(15, self._first_update)

    def _apply(self, data):
        s_pct   = round(data['five_hour']['utilization'])
        s_reset = fmt_reset(data['five_hour'].get('resets_at'))
        w_pct   = round(data['seven_day']['utilization'])
        w_reset = fmt_reset_weekly(data['seven_day'].get('resets_at'))

        self._last_pct = s_pct
        icon_path = make_icon(s_pct)
        self.indicator.set_icon_full(icon_path, f"{s_pct}%")

        dot = '🟢' if s_pct < 50 else '🟡' if s_pct < 75 else '🟠' if s_pct < 90 else '🔴'
        self.session_item.set_label(f"{dot}  5 saatlıq: {s_pct}%  (reset {s_reset})")

        dot2 = '🟢' if w_pct < 50 else '🟡' if w_pct < 75 else '🟠' if w_pct < 90 else '🔴'
        self.weekly_item.set_label(f"{dot2}  Həftəlik:  {w_pct}%  (reset {w_reset})")

        tokens = fetch_tokens()
        self.token_item.set_label(f"     Token (5s): {fmt_tokens(tokens)}")

    def update(self):
        try:
            data = fetch_usage()
            self._apply(data)
            self._next_interval = 120

        except urllib.error.HTTPError as e:
            if e.code == 429:
                raw_retry = e.headers.get("Retry-After", "?")
                retry_after = max(60, int(raw_retry)) if raw_retry != "?" else 60
                self._next_interval = retry_after
                mins = retry_after // 60
                secs = retry_after % 60
                time_str = f"{mins} dəq {secs} san" if secs else f"{mins} dəq"
                self.session_item.set_label(f"⏳  Rate limit — {time_str} sonra yenilənəcək  [server: {raw_retry}s]")
            else:
                self._next_interval = 300
                self.session_item.set_label(f"HTTP xəta: {e.code}")
        except Exception as e:
            self._next_interval = 120
            self.session_item.set_label(f"Xəta: {e}")

        return True

    def _first_update(self):
        self.update()
        GLib.timeout_add_seconds(self._next_interval, self._auto_update)
        return False

    def _manual_refresh(self):
        self._next_interval = 300
        self.update()

    def _auto_update(self):
        self.update()
        GLib.timeout_add_seconds(self._next_interval, self._auto_update)
        return False

if __name__ == '__main__':
    indicator = ClaudeIndicator()
    Gtk.main()
