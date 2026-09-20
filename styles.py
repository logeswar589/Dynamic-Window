"""
DynamicWin – Design Tokens & Style Constants
Pure black & white, macOS-inspired.
"""

BG_PRIMARY       = (10, 10, 10, 245)
BG_HOVER         = (20, 20, 20, 250)
ACCENT_WHITE     = (255, 255, 255)
TEXT_PRIMARY     = (255, 255, 255, 245)
TEXT_SECONDARY   = (180, 180, 180, 210)
TEXT_DIM         = (100, 100, 100, 160)
BORDER_COLOR     = (255, 255, 255, 20)
SHADOW_COLOR     = (0, 0, 0, 160)

ISLAND_IDLE_W    = 180
ISLAND_IDLE_H    = 36
ISLAND_EXPAND_W  = 340
ISLAND_EXPAND_H  = 160
ISLAND_MEDIA_W   = 340
ISLAND_MEDIA_H   = 76
CORNER_RADIUS    = 20
PAD              = 16
ANIM_DURATION_MS = 300

FONT_FAMILY      = "Segoe UI Variable"
FONT_FAMILY_FALLBACK = "Segoe UI"
FONT_SIZE_SM     = 11
FONT_SIZE_MD     = 13
FONT_SIZE_LG     = 15
FONT_SIZE_XL     = 20
FONT_WEIGHT_NORMAL = 400
FONT_WEIGHT_MEDIUM = 500
FONT_WEIGHT_BOLD   = 600

COLLAPSE_DELAY   = 1200
SYSMON_POLL_MS   = 2000
MEDIA_POLL_MS    = 1000
CLOCK_TICK_MS    = 1000
DESKTOP_POLL_MS  = 400
HOTCORNER_POLL_MS = 80
HOTCORNER_SIZE   = 8
SLIDE_DURATION   = 400
HOVER_MUSIC_DELAY = 500

_THEMES = {
    "black": {
        "BG_PRIMARY":     (10, 10, 10, 245),
        "BG_HOVER":       (20, 20, 20, 250),
        "ACCENT_WHITE":   (255, 255, 255),
        "TEXT_PRIMARY":   (255, 255, 255, 245),
        "TEXT_SECONDARY": (180, 180, 180, 210),
        "TEXT_DIM":       (100, 100, 100, 160),
        "BORDER_COLOR":   (255, 255, 255, 20),
        "SHADOW_COLOR":   (0, 0, 0, 160),
    },
    "white": {
        "BG_PRIMARY":     (240, 240, 242, 240),
        "BG_HOVER":       (228, 228, 230, 245),
        "ACCENT_WHITE":   (15, 15, 15),
        "TEXT_PRIMARY":   (15, 15, 15, 245),
        "TEXT_SECONDARY": (80, 80, 80, 210),
        "TEXT_DIM":       (140, 140, 140, 160),
        "BORDER_COLOR":   (0, 0, 0, 25),
        "SHADOW_COLOR":   (0, 0, 0, 80),
    },
}

CURRENT_THEME = "black"
GLASSY_UI = False


def set_theme(name: str):
    """Switch the active colour palette."""
    global BG_PRIMARY, BG_HOVER, ACCENT_WHITE, TEXT_PRIMARY, TEXT_SECONDARY
    global TEXT_DIM, BORDER_COLOR, SHADOW_COLOR, CURRENT_THEME
    if name not in _THEMES:
        return
    CURRENT_THEME = name
    t = _THEMES[name]
    BG_PRIMARY     = t["BG_PRIMARY"]
    BG_HOVER       = t["BG_HOVER"]
    ACCENT_WHITE   = t["ACCENT_WHITE"]
    TEXT_PRIMARY    = t["TEXT_PRIMARY"]
    TEXT_SECONDARY  = t["TEXT_SECONDARY"]
    TEXT_DIM        = t["TEXT_DIM"]
    BORDER_COLOR    = t["BORDER_COLOR"]
    SHADOW_COLOR    = t["SHADOW_COLOR"]


def set_glassy(enabled: bool):
    """Toggle glassy UI mode."""
    global GLASSY_UI
    GLASSY_UI = enabled
