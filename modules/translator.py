"""translator：只负责调 ModelScope API 把英文翻成中文。分块+重试+容错。"""
import time, requests
from pathlib import Path
from modules.config import STATE

KEY = "ms-5ff134d2-07a7-4ad8-8c54-9ad3628a51db"
ENDPOINT = "https://api-inference.modelscope.cn/v1/chat/completions"
MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"

CHUNK_CHARS = 30000
REQUEST_TIMEOUT = 300
MAX_RETRY = 3
BACKOFF = 5


def _call(block: str) -> str:
    # ModelScope API 走直连，不走 YouTube 的 SOCKS 代理
    import os
    saved = {k: os.environ.pop(k, None) for k in
             ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
              "ALL_PROXY", "all_proxy")}
    try:
        r = requests.post(ENDPOINT,
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "temperature": 0.3, "messages": [
                {"role": "system", "content": "You are a professional translator. Translate English to Simplified Chinese faithfully and naturally. Keep original paragraph/line structure. Do not summarize."},
                {"role": "user", "content": block},
            ]}, timeout=REQUEST_TIMEOUT)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"].strip()


def _translate_block(block: str) -> str:
    last = None
    for i in range(1, MAX_RETRY + 1):
        try:
            return _call(block)
        except Exception as e:
            last = e
            if i < MAX_RETRY:
                time.sleep(BACKOFF * i)
    raise last


def chunk_text(text: str):
    """按字数聚合成大块。先去连续重复行（源字幕/转写常有对齐错误）。"""
    # 去连续重复行
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


def translate_file(raw_path: Path, channel: str) -> str:
    """翻一个 _raw.txt -> _zh.txt。流式写：每块翻完立即追加，中断不丢。
    重翻时先清旧文件，避免续翻计数误差导致重复段落。
    返回 done/skipped/resume(n)/partial(n failed)"""
    zh = raw_path.with_name(raw_path.stem.replace("_raw", "_zh") + ".txt")
    if zh.exists() and zh.stat().st_size > 0 and not zh.read_text(encoding="utf-8").endswith("[翻译失败块"):
        # 已完整翻完（非失败残留），跳过
        if "[翻译失败块" not in zh.read_text(encoding="utf-8"):
            return "skipped"
    zh.unlink(missing_ok=True)  # 清掉旧的/部分的，从头流式写
    chunks = chunk_text(raw_path.read_text(encoding="utf-8"))
    failed = []
    with zh.open("a", encoding="utf-8") as fp:
        for i, blk in enumerate(chunks, 1):
            try:
                fp.write(_translate_block(blk) + "\n\n")
                fp.flush()
                print(f"    [{i}/{len(chunks)}] ok")
            except Exception as e:
                failed.append(i)
                fp.write(f"[翻译失败块{i}]\n\n")
                fp.flush()
                print(f"    [{i}/{len(chunks)}] FAIL: {e}")
            time.sleep(0.5)
    if failed:
        d = STATE / channel
        d.mkdir(parents=True, exist_ok=True)
        fp = d / "failed.json"
        import json
        data = json.loads(fp.read_text()) if fp.exists() else {}
        data[raw_path.name] = {"blocks_failed": failed}
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return f"partial({len(failed)} failed)"
    return "done"
