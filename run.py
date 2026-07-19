#!/usr/bin/env python3
"""run.py：总调度。一个频道跑一次完整流程：探测频率->去重->抓->翻->记录。
用法:
  python run.py <频道>        跑单个频道
  python run.py --all         跑全部4个频道
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "yt-transcribe"))

from modules.config import CHANNELS
from modules import yt_fetch, translator, recorder


def process_channel(chan):
    url = CHANNELS[chan]
    vids = yt_fetch.list_latest(url, n=10)
    if not vids:
        print(f"[{chan}] 取不到视频列表")
        return
    gap = recorder.median_gap_days(vids)
    print(f"[{chan}] 更新间隔≈{gap:.1f}天, 已记录{len(recorder.load(chan,'done.json'))}条")

    if not recorder.should_fetch(chan, gap):
        print(f"[{chan}] 未到抓取间隔，跳过")
        return

    done = recorder.load(chan, "done.json")
    target = next(((v, t) for v, t, _ in vids if v not in done), None)
    if not target:
        print(f"[{chan}] 最新几条都已处理")
        recorder.mark_fetch(chan, gap)
        return

    vid, title = target
    print(f"  抓: {title} ({vid})")
    raw = yt_fetch.download_subtitle(vid, title, chan)
    src = "subtitle"
    if not raw:
        print("  无字幕，转写...")
        raw = yt_fetch.download_audio_transcribe(vid, title, chan)
        src = "transcribe"
    if not raw:
        print(f"[{chan}] 抓取失败")
        return

    print("  翻译中...")
    res = translator.translate_file(Path(raw), chan)
    print("  翻译:", res)
    n = recorder.mark_done(chan, vid, title, src)
    recorder.mark_fetch(chan, gap)
    print(f"[{chan}] 完成，共{n}条")


def main():
    args = sys.argv[1:]
    if not args or args[0] == "--all":
        for c in CHANNELS:
            process_channel(c)
        return
    if args[0] not in CHANNELS:
        print("未知频道。可选:", ", ".join(CHANNELS))
        sys.exit(1)
    process_channel(args[0])


if __name__ == "__main__":
    main()
