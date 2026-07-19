"""yt_fetch：只负责跟 YouTube 打交道（取列表、下字幕、下音频转写）"""
import subprocess, re
from pathlib import Path
from modules.config import BIN, CACHE, TRANSCRIPTS, PROXY, JS_RUNTIMES


def _env():
    env = dict(__import__("os").environ)
    env["PATH"] = str(BIN.parent) + ":" + env.get("PATH", "")
    env["HTTP_PROXY"] = PROXY
    env["HTTPS_PROXY"] = PROXY
    env["http_proxy"] = PROXY
    env["https_proxy"] = PROXY
    return env


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, env=_env())


def _ytdlp(*args):
    return _run(["yt-dlp", "--proxy", PROXY, "--js-runtimes", JS_RUNTIMES] + list(args))


def sanitize(s):
    return re.sub(r'[\\/:*?"<>|]', '_', s)[:80]


def list_latest(channel_url, n=10):
    """返回 [(id, title, upload_date), ...]"""
    uploads = channel_url.rstrip("/") + "/videos"
    r = _ytdlp("--flat-playlist", "--playlist-end", str(n),
               "--print", "%(id)s\t%(title)s\t%(upload_date)s", uploads)
    if r.returncode != 0 or not r.stdout.strip():
        r = _ytdlp("--flat-playlist", "--playlist-end", str(n),
                   "--print", "%(id)s\t%(title)s\t%(upload_date)s", channel_url)
    out = []
    for line in r.stdout.strip().splitlines():
        p = line.split("\t")
        out.append((p[0].strip(), p[1].strip() if len(p) > 1 else "untitled",
                    p[2].strip() if len(p) > 2 else ""))
    return out


def download_subtitle(vid, title, channel):
    """下英文字幕 -> 返回 _raw.txt 路径 或 None"""
    out_dir = TRANSCRIPTS / channel
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{vid}_{sanitize(title)}"
    cmd = ["yt-dlp", "--proxy", PROXY, "--skip-download",
           "--write-subs", "--write-auto-subs", "--sub-langs", "en.*",
           "--convert-subs", "srt",
           "-o", str(out_dir / (base + ".%(ext)s")),
           f"https://www.youtube.com/watch?v={vid}"]
    if _run(cmd).returncode != 0:
        return None
    for ext in ("srt", "vtt"):
        for p in sorted(out_dir.glob(f"{base}*.{ext}")):
            text = p.read_text(errors="ignore")
            lines = []
            for line in text.splitlines():
                s = line.strip()
                if not s or re.match(r'^\d+$', s):
                    continue
                if re.match(r'^\d\d:\d\d:\d\d[.,]\d+\s*-->', s):
                    continue
                if s == "WEBVTT":
                    continue
                lines.append(s)
            if lines:
                txt = out_dir / f"{base}_raw.txt"
                txt.write_text("\n".join(lines), encoding="utf-8")
                p.unlink()
                return str(txt)
            p.unlink()
    return None


def download_audio_transcribe(vid, title, channel):
    """无字幕：下音频 + faster-whisper 转写 -> _raw.txt 路径 或 None"""
    out_dir = TRANSCRIPTS / channel
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{vid}_{sanitize(title)}"
    audio = CACHE / f"{vid}.wav"
    if _ytdlp("-x", "--audio-format", "best", "-o", str(CACHE / f"{vid}.%(ext)s"),
              f"https://www.youtube.com/watch?v={vid}").returncode != 0:
        return None
    for f in CACHE.glob(f"{vid}.*"):
        if f.suffix == ".wav":
            continue
        _run([str(BIN), "-y", "-i", str(f), "-ar", "16000", "-ac", "1",
              "-c:a", "pcm_s16le", str(audio)])
        f.unlink()
        break
    if not audio.exists():
        return None
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(audio), language="en", beam_size=5)
    txt = out_dir / f"{base}_raw.txt"
    with txt.open("w", encoding="utf-8") as fp:
        for s in segs:
            fp.write(s.text.strip() + "\n")
    audio.unlink()
    return str(txt)
