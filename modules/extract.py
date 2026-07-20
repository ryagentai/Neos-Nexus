"""extract：把英文转录稿萃取为一篇中文财经新闻稿（彭博风格）。
不逐句翻译，而是理解全文后重写——剔除口语填充词、闲聊、广告，
保留核心事实/数据/观点，分段落、有导语，读起来像 Bloomberg 报道。
"""
import time, os, json, requests
from pathlib import Path
from modules.config import STATE

KEY = "ms-5ff134d2-07a7-4ad8-8c54-9ad3628a51db"
ENDPOINT = "https://api-inference.modelscope.cn/v1/chat/completions"
# 模型池：今天额度内的可用模型（撞 429/限流自动轮换下一个）
MODELS = [
    "Qwen/Qwen3.5-122B-A10B",
    "Qwen/Qwen3.5-27B",
    "deepseek-ai/DeepSeek-V3.2",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
]

CHUNK_CHARS = 28000
REQUEST_TIMEOUT = 300
MAX_RETRY = 3
BACKOFF = 5

SYSTEM_PROMPT = """你是一位眼光毒辣的财经评论员，文风对标 Patrick Boyle 那种——有观点、有锋芒、敢下判断，不是四平八稳的官媒通稿。

任务：把视频转录稿（英文，含口语、填充词、闲聊）萃取并重写成一篇**有深度的中文评论**。

要求：
1. 彻底剔除口语填充词与闲聊广告，只留干货。
2. 抓核心论点、反直觉洞察、争议点、作者/嘉宾的真实立场——而不是罗列事实。
3. 文风要有态度：可以用锐利的比喻、直接的判断、带刺的反问。让读者感受到"这人在表达观点"，不是在念说明书。
4. 保留关键数据/人名/机构名作支撑，但数据服务于论点，不要堆砌。
5. 分段落、有节奏：开头一句话点出最反直觉或最有争议的点，后面展开。
6. 不虚构、不添加稿外信息；信息不足宁可少写。
7. 输出纯中文正文，无序号、无元说明、不用 Markdown 列表。
8. 长度依内容 300–800 字，长访谈可更长。

只输出评论正文本身。"""


def _call(block: str, model: str) -> str:
    saved = {k: os.environ.pop(k, None) for k in
             ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
              "ALL_PROXY", "all_proxy")}
    try:
        r = requests.post(ENDPOINT,
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            json={"model": model, "temperature": 0.5, "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "以下是视频转录稿，请萃取为一篇有锋芒的中文深度评论：\n\n" + block},
            ]}, timeout=REQUEST_TIMEOUT)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"].strip()


def _extract_block(block: str) -> str:
    """撞 429/限流时自动轮换模型池里的下一个，不依赖单一模型额度。"""
    last = None
    for attempt in range(1, MAX_RETRY * len(MODELS) + 1):
        model = MODELS[(attempt - 1) % len(MODELS)]
        try:
            return _call(block, model)
        except Exception as e:
            last = e
            if attempt < MAX_RETRY * len(MODELS):
                time.sleep(BACKOFF)
    raise last


def chunk_text(text: str):
    lines = text.split("\n")
    cleaned = []
    prev = None
    for ln in lines:
        s = ln.strip()
        if s and s == prev:
            continue
        cleaned.append(ln)
        prev = s
    text = "\n".join(cleaned)
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 1 <= CHUNK_CHARS:
            cur = (cur + "\n" + p).strip()
        else:
            if cur:
                chunks.append(cur)
            if len(p) > CHUNK_CHARS:
                for i in range(0, len(p), CHUNK_CHARS):
                    chunks.append(p[i:i + CHUNK_CHARS])
                cur = ""
            else:
                cur = p
    if cur:
        chunks.append(cur)
    return chunks


# 频道 -> 媒体/定位说明（写在抬头，让你一眼看出信息源分量）
CHANNEL_META = {
    "OddLots_NA":      ("Odd Lots（彭博王牌财经访谈）", "Bloomberg"),
    "ILTB_NA":         ("Invest Like the Best（顶级投资者访谈）", "YouTube"),
    "WSB_NA":          ("We Study Billionaires（巴菲特式价值投资访谈）", "The Investor's Podcast"),
    "RealVision_NA":   ("Real Vision（宏观/市场深度访谈）", "Real Vision"),
    "PatrickBoyle_NA": ("Patrick Boyle（金融史/市场结构深度分析）", "YouTube"),
    "FT_EU":           ("Financial Times（英国顶流财经媒体）", "FT"),
    "BBCWS_EU":        ("BBC World Service（英国广播公司国际台）", "BBC"),
    "FTAlpha_EU":      ("FT Alphaville（FT 市场专栏）", "FT"),
    "NikkeiAsia_AS":   ("Nikkei Asia（日本经济新闻亚洲版）", "Nikkei"),
    "CNA_AS":          ("Channel News Asia（新加坡亚洲新闻台）", "CNA"),
}


def _header(meta):
    chan = meta.get("channel", "")
    src_name, media = CHANNEL_META.get(chan, (chan, "YouTube"))
    title = meta.get("title", "")
    date = meta.get("date", "")
    date_fmt = ""
    if date and len(date) == 8:
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    lines = [
        f"【来源】{src_name}",
        f"【媒体】{media}",
        f"【发布】{date_fmt or '未知'}",
        f"【原题】{title}",
        "---",
    ]
    return "\n".join(lines) + "\n"


def extract_file(raw_path: Path, channel: str, meta: dict = None) -> str:
    """萃取一个 _raw.txt -> _news.txt（不覆盖 raw/zh）。带元信息抬头。"""
    meta = meta or {"channel": channel, "title": "", "date": ""}
    news = raw_path.with_name(raw_path.stem.replace("_raw", "_news") + ".txt")
    if news.exists() and news.stat().st_size > 0 and "[萃取失败块" not in news.read_text(encoding="utf-8"):
        return "skipped"
    news.unlink(missing_ok=True)
    chunks = chunk_text(raw_path.read_text(encoding="utf-8"))
    failed = []
    with news.open("a", encoding="utf-8") as fp:
        fp.write(_header(meta))
        for i, blk in enumerate(chunks, 1):
            try:
                fp.write(_extract_block(blk) + "\n\n")
                fp.flush()
                print(f"    [{i}/{len(chunks)}] ok")
            except Exception as e:
                failed.append(i)
                fp.write(f"[萃取失败块{i}]\n\n")
                fp.flush()
                print(f"    [{i}/{len(chunks)}] FAIL: {e}")
            time.sleep(0.5)
    if failed:
        d = STATE / channel
        d.mkdir(parents=True, exist_ok=True)
        fp = d / "failed.json"
        data = json.loads(fp.read_text()) if fp.exists() else {}
        data[raw_path.name] = {"blocks_failed": failed}
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return f"partial({len(failed)} failed)"
    return "done"
