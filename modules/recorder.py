"""recorder：只负责读写状态文件（去重记录 + 抓取频率状态）"""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from modules.config import STATE


def load(channel, name):
    p = STATE / channel / name
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def save(channel, name, data):
    p = STATE / channel / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_done(channel, vid, title, source):
    done = load(channel, "done.json")
    done[vid] = {"title": title, "source": source,
                 "processed_at": datetime.now(timezone.utc).isoformat()}
    save(channel, "done.json", done)
    return len(done)


def mark_fetch(channel, gap_days):
    save(channel, "fetch_state.json",
         {"last_fetch": datetime.now(timezone.utc).isoformat(), "gap_days": gap_days})


def median_gap_days(videos):
    dates = []
    for _, _, ud in videos:
        if re.match(r'^\d{8}$', ud or ""):
            dates.append(datetime.strptime(ud, "%Y%m%d"))
    dates.sort()
    if len(dates) < 2:
        return 1.0
    gaps = sorted(g for g in ((dates[i+1]-dates[i]).days for i in range(len(dates)-1)) if g >= 0)
    return float(gaps[len(gaps)//2]) or 1.0


def should_fetch(channel, gap_days):
    st = load(channel, "fetch_state.json")
    last = st.get("last_fetch")
    if not last:
        return True
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() / 86400
    return elapsed >= max(gap_days * 0.6, 0.3)
