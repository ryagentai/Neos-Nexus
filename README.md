# Neos Nexus — YouTube 财经频道抓取+翻译

自动抓取 4 个财经 YouTube 频道最新视频，提取英文文本（字幕优先，无字幕则 whisper 转写），
调用 ModelScope (Qwen3-235B) 全文翻译为中文。

## 结构（小模块）
```
run.py              总调度：跑单频道或 --all
translate_channel.py 补翻入口（薄包装）
modules/
  config.py        配置（频道/代理/路径）
  yt_fetch.py      抓 YouTube（列表/字幕/转写）
  translator.py    翻译（分块+去重+重试+直连 API）
  recorder.py      状态记录（去重/频率探测）
```

## 依赖
- 代理：本机 xray 监听 127.0.0.1:1080（走 3xui 干净出口）
- yt-dlp + node（JS 运行时）+ ffmpeg（在 bin/）
- faster-whisper（venv，CPU int8）
- ModelScope API key（modules/translator.py 内 KEY）

## 用法
```
python run.py PatrickBoyle      # 单频道
python run.py --all             # 全部
python translate_channel.py BloombergTV  # 补翻未译的
```
