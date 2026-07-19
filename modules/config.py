"""配置：频道列表、代理、路径。改这里就行，不碰逻辑。"""
from pathlib import Path

ROOT = Path.home() / "yt-transcribe"
BIN = ROOT / "bin" / "ffmpeg"
TRANSCRIPTS = ROOT / "transcripts"
CACHE = ROOT / "cache"
STATE = ROOT / "state"

CHANNELS = {
    "BloombergTV":  "https://www.youtube.com/@markets",
    "PatrickBoyle": "https://www.youtube.com/@PBoyle",
    "MoneyMacro":   "https://www.youtube.com/@MoneyMacro",
    "OddLots":      "https://www.youtube.com/@BloombergPodcasts",
}

PROXY = "socks5h://127.0.0.1:1080"
JS_RUNTIMES = "node"
