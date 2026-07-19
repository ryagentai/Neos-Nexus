#!/usr/bin/env python3
"""translate_channel.py：补翻某频道下所有未翻译的 _raw.txt（薄入口，只调 translator 模块）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "yt-transcribe"))
from modules.config import CHANNELS, TRANSCRIPTS
from modules import translator

if len(sys.argv) < 2 or sys.argv[1] not in CHANNELS:
    print("用法: python translate_channel.py <频道>  可选:", ", ".join(CHANNELS))
    sys.exit(1)
chan = sys.argv[1]
d = TRANSCRIPTS / chan
for f in sorted(d.glob("*_raw.txt")):
    print("翻:", f.name)
    print("  ->", translator.translate_file(f, chan))
