#!/usr/bin/env python3
"""Neos Nexus 常驻守护：每天欧洲 10:00 CEST 自动跑全套，不依赖 cron 600s 限制。
流程：抓最新视频→萃取中文深度稿→清过程文件→推GitHub→写完成标记(/tmp/neos_done.json)。
用 nohup 后台常驻：nohup python3 daemon.py > /tmp/neos_daemon.log 2>&1 &
"""
import os, sys, subprocess, glob, zipfile, json, time, threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path.home() / "yt-transcribe"
os.chdir(ROOT)
SSH = "ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def do_daily():
    """跑一轮：抓→萃→清→推GitHub→写完成标记"""
    stamp = datetime.now().strftime("%Y-%m-%d")
    log_lines = []
    try:
        # 1. 抓+萃+清（venv python）
        env = 'export PATH="$HOME/yt-transcribe/venv/bin:$PATH" && '
        r = run(env + "python run.py --all 2>&1 | tail -40")
        log_lines.append(r.stdout[-1500:])

        # 2. 统计 news
        news = sorted(glob.glob("transcripts/*/*_news.txt"))
        n = len(news)

        # 3. 打包
        zip_path = "/tmp/neos_daily.zip"
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if n > 0:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in news:
                    z.write(f, os.path.basename(f))

        # 4. 推 GitHub（SSH key，无凭证）
        run(f'{SSH} git add -A')
        run(f'git -c user.email="ryan@neos.local" -c user.name="Neos" commit -q -m "daily {stamp}: {n} news"')
        pr = run(f'GIT_SSH_COMMAND="{SSH}" git push -u origin master 2>&1 | tail -3')
        log_lines.append(pr.stdout)

        # 5. 写完成标记（供轻量 cron 发文件）
        done = {
            "date": stamp,
            "count": n,
            "zip": zip_path if n > 0 else "",
            "ts": datetime.now().isoformat(),
        }
        Path("/tmp/neos_done.json").write_text(json.dumps(done, ensure_ascii=False))
        log_lines.append(f"DONE|{n}|{zip_path if n>0 else ''}")
    except Exception as e:
        Path("/tmp/neos_done.json").write_text(json.dumps(
            {"date": stamp, "count": -1, "error": str(e), "ts": datetime.now().isoformat()},
            ensure_ascii=False))
    finally:
        Path("/tmp/neos_daemon.log").open("a", encoding="utf-8").write(
            "\n=== " + stamp + " ===\n" + "\n".join(log_lines) + "\n")

def next_trigger():
    """下一个欧洲 10:00 CEST（UTC+2 夏令时 / UTC+1 冬令时）。简化：用 UTC 08:00（夏令时=CEST10:00）。"""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target + timedelta(days=1)
    return target

def loop():
    while True:
        t = next_trigger()
        wait = (t - datetime.now(timezone.utc)).total_seconds()
        print(f"[{datetime.now()}] 下次运行: {t} (约 {wait/3600:.1f}h 后)")
        time.sleep(wait)
        print(f"[{datetime.now()}] 开始每日运行")
        do_daily()

if __name__ == "__main__":
    print("Neos daemon started")
    loop()
