"""配置：频道列表、代理、路径。改这里就行，不碰逻辑。"""
from pathlib import Path

ROOT = Path.home() / "yt-transcribe"
BIN = ROOT / "bin" / "ffmpeg"
TRANSCRIPTS = ROOT / "transcripts"
CACHE = ROOT / "cache"
STATE = ROOT / "state"

# 全球顶流深度/大咖访谈财经源（用频道ID避免handle失效；代理出口验证可抓取）
# key=频道简称，value=频道视频页URL（channel ID 形式最稳）
CHANNELS = {
    # 北美：顶级投资者长访谈 + 深度分析
    "OddLots_NA":        "https://www.youtube.com/channel/UChF5O40UBqAc82I7-i5ig6A/videos",
    "ILTB_NA":           "https://www.youtube.com/channel/UCpQBb0fToph3jrDulwz1iUQ/videos",
    "WSB_NA":            "https://www.youtube.com/channel/UCBOkqyWxbp8jtcsvcHB7qog/videos",
    "RealVision_NA":     "https://www.youtube.com/channel/UCGXWKlq1Oxr3ddEtmKhAkPg/videos",
    "PatrickBoyle_NA":   "https://www.youtube.com/channel/UCASM0cgfkJxQ1ICmRilfHLw/videos",
    # 欧洲：机构深度 + 宏观访谈 + 市场专栏
    "FT_EU":             "https://www.youtube.com/@FinancialTimes/videos",
    "BBCWS_EU":          "https://www.youtube.com/@BBCWorldService/videos",
    "FTAlpha_EU":        "https://www.youtube.com/@FTAlphaville/videos",
    # 亚洲：亚太战略/资源深度 + 亚洲视角
    "NikkeiAsia_AS":     "https://www.youtube.com/@NikkeiAsia/videos",
    "CNA_AS":            "https://www.youtube.com/@channelnewsasia/videos",
}

# 每频道抓取最新条数
PER_CHANNEL = 5

PROXY = "socks5h://127.0.0.1:1080"
JS_RUNTIMES = "node"
