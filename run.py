#!/usr/bin/env python3
"""run.py：总调度。每频道抓最新 PER_CHANNEL 条 -> 英文原文 -> 萃取中文新闻稿 -> 记录防重复。
用法:
  python run.py <频道key>   跑单个频道
  python run.py --all       跑全部频道
  python run.py --dry       只列将抓的视频，不下载不萃取
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "yt-transcribe"))

from modules.config import CHANNELS, PER_CHANNEL, TRANSCRIPTS
from modules import yt_fetch, extract, recorder


def process_channel(chan):
    url = CHANNELS[chan]
    vids = yt_fetch.list_latest(url, n=PER_CHANNEL)
    if not vids:
        print(f"[{chan}] 取不到视频列表")
        return
    print(f"[{chan}] 最新 {len(vids)} 条")

    done = recorder.load(chan, "done.json")
    pending = [(v, t, d) for v, t, d in vids if v not in done]
    if not pending:
        print(f"[{chan}] 都已处理，跳过")
        return

    for vid, title, udate in pending:
        print(f"  抓: {title} ({vid})")
        raw = yt_fetch.download_subtitle(vid, title, chan)
        src = "subtitle"
        if not raw:
            print("    无字幕，转写...")
            raw = yt_fetch.download_audio_transcribe(vid, title, chan)
            src = "transcribe"
        if not raw:
            print(f"    [{chan}] 抓取失败，跳过")
            continue

        print("    萃取新闻稿...")
        meta = {"channel": chan, "title": title, "date": udate or ""}
        res = extract.extract_file(Path(raw), chan, meta)
        print("    萃取:", res)
        recorder.mark_done(chan, vid, title, src)
        # 清理过程文件：萃取成功后只留 _news.txt，删 raw/srt/zh + cache音频
        if res in ("done", "skipped") or res.startswith("partial"):
            from pathlib import Path as _P
            base = Path(raw).stem.replace("_raw", "")
            out_dir = Path(raw).parent
            for pat in (f"{base}_raw.txt", f"{base}.*.srt", f"{base}_zh.txt", f"{base}*.en*srt"):
                for f in out_dir.glob(pat):
                    f.unlink(missing_ok=True)
            # 清该视频的 cache 音频
            for f in CACHE.glob(f"{vid}.*"):
                f.unlink(missing_ok=True)
            print("    已清理过程文件")
    print(f"[{chan}] 完成")


def main():
    args = sys.argv[1:]
    mode = "--all" if not args or args[0] == "--all" else args[0]
    if mode == "--dry":
        for c, u in CHANNELS.items():
            vids = yt_fetch.list_latest(u, n=PER_CHANNEL)
            print(f"### {c}")
            for v, t, _ in (vids or []):
                print(f"  {v}  {t}")
        return
    if mode == "--redo":
        # 删掉所有 news 重萃（换 prompt / 补失败）
        import shutil
        for f in Path(TRANSCRIPTS).rglob("*_news.txt"):
            f.unlink()
        print("已清旧 news，重跑所有频道")
        mode = "--all"
    if mode == "--all":
        for c in CHANNELS:
            process_channel(c)
        return
    if mode not in CHANNELS:
        print("未知频道。可选:", ", ".join(CHANNELS))
        sys.exit(1)
    process_channel(mode)


if __name__ == "__main__":
    main()
