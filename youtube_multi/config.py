"""
Snapmaker U1 & Bambu H2C YouTube 反馈提取系统 — 配置常量

所有搜索词、已知频道、正则模式、主题关键词均在此定义。
支持三类视频分析：U1 评测、H2C/Vortek 评测、综合对比。
"""

import os
from pathlib import Path

# --- 路径常量 ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PER_VIDEO_DATA_DIR = DATA_DIR / "per_video"
REPORTS_DIR = BASE_DIR / "reports"
PER_VIDEO_REPORTS_DIR = REPORTS_DIR / "per_video"

# --- 时间范围 ---
# 2025-11-15 起：量产机开始到达用户手中
PUBLISHED_AFTER = "2025-11-15T00:00:00Z"

# --- 搜索关键词 ---
SEARCH_QUERIES_U1 = [
    "Snapmaker U1 review",
    "Snapmaker U1 unboxing",
    "Snapmaker U1 vs Bambu",
    "Snapmaker U1 multicolor",
    "Snapmaker U1 tool changer",
    "Snapmaker U1 first impressions",
    "Snapmaker U1 problems",
    "Snapmaker U1 print quality",
    "Snapmaker U1 setup",
    "Snapmaker U1 speed test",
    "Snapmaker U1 vs H2C",
    "Snapmaker U1 long term",
    "Snapmaker U1 tips",
]

SEARCH_QUERIES_H2C = [
    "Bambu Lab H2C review",
    "Bambu H2C unboxing",
    "Bambu H2C first impressions",
    "Bambu H2C print quality",
    "Bambu H2C problems",
    "Bambu H2C setup",
    "Bambu H2C speed test",
    "Bambu H2C long term",
    "Bambu Lab Vortek review",
    "Bambu Vortek unboxing",
    "Vortek 3D printer review",
    "H2C tool changer review",
]

SEARCH_QUERIES_COMPARISON = [
    "Snapmaker U1 vs Bambu H2C",
    "Snapmaker U1 vs H2C",
    "U1 vs H2C comparison",
    "Snapmaker vs Bambu tool changer",
    "Snapmaker U1 vs Bambu Vortek",
    "Bambu H2C vs Snapmaker U1",
    "best multi color 3d printer 2025",
]

SEARCH_QUERIES = SEARCH_QUERIES_U1 + SEARCH_QUERIES_H2C + SEARCH_QUERIES_COMPARISON

# --- 已知评测频道 ---
KNOWN_REVIEWERS = [
    {"channel": "Adam Savage's Tested", "search": "Tested Snapmaker U1"},
    {"channel": "stlDenise3D / Tom's Hardware", "search": "stlDenise3D Snapmaker U1"},
    {"channel": "3D Printing Nerd", "search": "3D Printing Nerd Snapmaker U1"},
    {"channel": "Teaching Tech", "search": "Teaching Tech Snapmaker U1"},
    {"channel": "Makers Muse", "search": "Makers Muse Snapmaker U1"},
    {"channel": "3DPrint.com", "search": "3DPrint Snapmaker U1"},
    {"channel": "Snapmaker Official", "search": "Snapmaker U1 official"},
    {"channel": "DukeDoks", "search": "DukeDoks Snapmaker U1"},
    {"channel": "ModBot", "search": "ModBot Snapmaker U1"},
    {"channel": "3DJake", "search": "3DJake Snapmaker U1"},
    {"channel": "Aurora Tech", "search": "Aurora Tech Snapmaker U1"},
    {"channel": "Uncle Jesse", "search": "Uncle Jesse Snapmaker U1"},
    {"channel": "Lost In Tech", "search": "Lost In Tech Snapmaker U1"},
    {"channel": "BV3D", "search": "BV3D Snapmaker U1"},
    {"channel": "The 3D Print General", "search": "3D Print General Snapmaker U1"},
    {"channel": "Thomas Sanladerer", "search": "Thomas Sanladerer Snapmaker U1"},
    {"channel": "CNC Kitchen", "search": "CNC Kitchen Snapmaker U1"},
    {"channel": "Frankly Built", "search": "Frankly Built Snapmaker U1"},
]

KNOWN_REVIEWERS_H2C = [
    {"channel": "3D Printing Nerd", "search": "3D Printing Nerd Bambu H2C"},
    {"channel": "Teaching Tech", "search": "Teaching Tech Bambu H2C"},
    {"channel": "Makers Muse", "search": "Makers Muse Bambu H2C"},
    {"channel": "Thomas Sanladerer", "search": "Thomas Sanladerer Bambu H2C"},
    {"channel": "CNC Kitchen", "search": "CNC Kitchen Bambu H2C"},
    {"channel": "ModBot", "search": "ModBot Bambu H2C"},
    {"channel": "Uncle Jesse", "search": "Uncle Jesse Bambu H2C"},
    {"channel": "BV3D", "search": "BV3D Bambu H2C"},
    {"channel": "The 3D Print General", "search": "3D Print General Bambu H2C"},
    {"channel": "Frankly Built", "search": "Frankly Built Bambu H2C"},
]

KNOWN_CHANNEL_NAMES = [r["channel"].lower() for r in KNOWN_REVIEWERS]

# --- 视频分类关键词 ---
U1_KEYWORDS = ["snapmaker", "u1", "snap maker", "snapswap"]
H2C_KEYWORDS = ["h2c", "h2d", "vortek", "bambu lab h2c", "bambu h2c"]
BAMBU_BROAD_KEYWORDS = ["bambu", "bamboo", "bambu lab"]
COMPARISON_SIGNALS = ["vs", "versus", "comparison", "compared", "head to head", "showdown", "对比", "pk"]

VIDEO_CATEGORIES = {
    "u1_review": "快造U1评测",
    "h2c_review": "拓竹H2C/Vortek评测",
    "comparison": "综合评测",
}

# --- 相关性过滤 ---
RELEVANCE_KEYWORDS = ["snapmaker", "u1", "snap maker", "bambu", "h2c", "h2d", "vortek"]

# --- 赞助/样机检测正则 ---
SPONSOR_PATTERNS = {
    "explicit_sponsor": [
        r"sponsor(?:ed|ship)?\s+(?:by|from)\s+snapmaker",
        r"snapmaker\s+sponsor",
        r"paid\s+(?:promotion|partnership|collaboration)",
        r"this\s+video\s+(?:is|was)\s+sponsored",
        r"brought\s+to\s+you\s+by\s+snapmaker",
        r"#(?:ad|sponsored|paid)",
        r"(?:ad|advertisement)\s*[:\-\u2013]",
    ],
    "review_sample": [
        r"review\s+(?:unit|sample|copy)",
        r"(?:sent|provided|supplied)\s+(?:by|from|courtesy)\s+(?:of\s+)?snapmaker",
        r"snapmaker\s+(?:sent|provided|supplied)",
        r"(?:pre-?production|beta)\s+(?:unit|sample|machine|printer)",
        r"(?:received|got)\s+(?:this|the)\s+(?:printer|machine|unit)\s+(?:from|courtesy)",
        r"disclosure\s*:\s*review\s+sample",
        r"thank(?:s)?\s+(?:to\s+)?snapmaker\s+for\s+(?:sending|providing)",
    ],
    "affiliate": [
        r"affiliate\s+link",
        r"commission\s+(?:at|from)",
        r"use\s+(?:my|our|this)\s+(?:link|code)\s+(?:to|for)",
        r"(?:discount|coupon)\s+code",
    ],
    "self_purchased": [
        r"(?:i|we)\s+(?:bought|purchased|backed|pledged)",
        r"kickstarter\s+backer",
        r"(?:my|our)\s+(?:own\s+)?money",
        r"not\s+(?:a\s+)?sponsor",
        r"(?:i|we)\s+(?:paid|bought)\s+(?:for\s+)?(?:this|it)\s+(?:myself|ourselves)",
    ],
}

# --- 内容关键信息检测模式 ---
KEY_INFO_PATTERNS = {
    "verdict_positive": {
        "patterns": [
            r"(?:i |we |would |definitely |highly )recommend",
            r"(?:really |absolutely |totally )(?:love|impressed|amazing)",
            r"game.?changer", r"best .{0,20} printer",
            r"worth (?:every|the) (?:penny|dollar|money)", r"no.?brainer",
        ],
        "label": "\u6b63\u9762\u8bc4\u4ef7/\u63a8\u8350"
    },
    "verdict_negative": {
        "patterns": [
            r"(?:don'?t|wouldn'?t|cannot|can'?t) recommend",
            r"(?:really |very |quite |so )disappoint",
            r"deal.?breaker", r"not worth",
            r"(?:send|sent) (?:it )?back", r"return(?:ed|ing)?",
        ],
        "label": "\u8d1f\u9762\u8bc4\u4ef7/\u4e0d\u63a8\u8350"
    },
    "print_quality": {
        "patterns": [
            r"print quality", r"layer lines?", r"surface finish",
            r"stringing", r"blob", r"z.?seam", r"dimensional accuracy",
        ],
        "label": "\u6253\u5370\u8d28\u91cf"
    },
    "tool_change": {
        "patterns": [
            r"tool.?chang", r"tool.?swap", r"snap.?swap",
            r"tool.?head",
            r"(?:\d+)\s*(?:second|sec).{0,10}(?:swap|change)",
        ],
        "label": "\u6362\u5934/\u6362\u8272\u673a\u5236"
    },
    "waste_comparison": {
        "patterns": [
            r"(?:filament |material )?waste", r"prime tower", r"purge",
            r"no waste", r"poop.?chute", r"(?:\d+)\s*(?:g|gram)",
        ],
        "label": "\u8017\u6750\u6d6a\u8d39"
    },
    "speed_benchmark": {
        "patterns": [
            r"\d+\s*(?:mm/?s|millimeters?\s*per\s*second)",
            r"print(?:ing)? speed",
            r"(?:fast|slow)er than",
            r"benchy.{0,20}(?:minute|min|time)",
        ],
        "label": "\u901f\u5ea6\u6d4b\u8bd5/\u5bf9\u6bd4"
    },
    "noise_level": {
        "patterns": [
            r"\d+\s*(?:db|decibel)",
            r"(?:very |really |quite )?(?:loud|noisy|quiet|silent)",
            r"noise (?:level|test)",
        ],
        "label": "\u566a\u97f3\u6c34\u5e73"
    },
    "price_value": {
        "patterns": [
            r"(?:\$|USD)\s*\d+", r"\d+\s*(?:dollars?|bucks)",
            r"(?:price|cost|expensive|affordable|cheap)",
            r"value (?:for|proposition)",
        ],
        "label": "\u4ef7\u683c/\u6027\u4ef7\u6bd4"
    },
    "vs_competitor": {
        "patterns": [
            r"(?:bambu|bamboo)\s*(?:lab)?",
            r"(?:p1s|p1p|x1c|a1|ams|h2[cd])",
            r"prusa\s*(?:xl|mk4|mmu|core)",
            r"creality",
            r"(?:compared?|versus|vs\.?)\s+",
        ],
        "label": "\u7ade\u54c1\u5bf9\u6bd4"
    },
    "enclosure": {
        "patterns": [
            r"enclosure", r"(?:top )?(?:cover|hat|lid)", r"open.?frame",
        ],
        "label": "\u5916\u58f3/\u5bc6\u5c01"
    },
    "firmware_software": {
        "patterns": [
            r"firmware",
            r"(?:orca|cura|bambu|snapmaker)\s*(?:slicer|studio)",
            r"klipper", r"update", r"(?:software )?bug",
        ],
        "label": "\u56fa\u4ef6/\u8f6f\u4ef6"
    },
    "reliability": {
        "patterns": [
            r"reliab", r"(?:success|failure) rate",
            r"(?:print )?fail", r"long.?term",
        ],
        "label": "\u53ef\u9760\u6027/\u957f\u671f\u4f7f\u7528"
    },
    "quality_issues": {
        "patterns": [
            r"quality\s*(?:issue|problem|control)", r"defect",
            r"(?:plastic|shell|panel)\s*(?:crack|break|loose)",
            r"(?:pogo\s*pin|contact)\s*(?:error|issue|problem)",
        ],
        "label": "\u54c1\u63a7\u95ee\u9898"
    },
    "specific_numbers": {
        "patterns": [
            r"\d+\.?\d*\s*(?:mm|cm|inch|\u00b0C|degrees|watts?|amps?|volts?)",
            r"\d+\s*(?:hours?|minutes?|seconds?)\s+(?:print|total)",
        ],
        "label": "\u5177\u4f53\u53c2\u6570/\u6570\u636e"
    },
}

# --- 评论主题关键词 ---
TOPIC_KEYWORDS = {
    "print_quality": ["print quality", "layer", "surface", "finish", "detail", "stringing", "blob", "artifact"],
    "tool_change": ["tool change", "tool swap", "snapswap", "head swap", "nozzle swap", "tool head"],
    "speed": ["speed", "fast", "slow", "print time", "mm/s", "acceleration"],
    "noise": ["noise", "loud", "quiet", "silent", "sound", "decibel", "db"],
    "waste_filament": ["waste", "purge", "filament waste", "prime tower", "poop", "trash"],
    "enclosure": ["enclosure", "top cover", "lid", "enclosed", "chamber", "top hat"],
    "calibration": ["calibration", "calibrate", "level", "offset", "alignment", "z offset"],
    "firmware_software": ["firmware", "software", "klipper", "orca", "slicer", "update", "bug", "crash"],
    "camera": ["camera", "timelapse", "time lapse", "monitoring"],
    "wifi_connectivity": ["wifi", "wi-fi", "lan", "cloud", "connection", "connect"],
    "materials": ["pla", "petg", "tpu", "abs", "asa", "carbon fiber", "flexible", "material"],
    "nozzle": ["nozzle", "hardened steel", "stainless", "hotend", "clog"],
    "build_volume": ["build volume", "print size", "270", "bed size", "build plate"],
    "price_value": ["price", "worth", "value", "expensive", "cheap", "cost", "dollar", "$"],
    "vs_bambu": ["bambu", "bamboo", "p1s", "p1p", "x1c", "x1", "a1", "ams", "h2d", "h2c"],
    "vs_prusa": ["prusa", "xl", "mk4", "mmu", "core one"],
    "vs_creality": ["creality", "k1", "ender"],
    "setup_unboxing": ["setup", "unbox", "assembly", "install", "out of box", "first print"],
    "reliability": ["reliable", "reliability", "fail", "error", "crash", "jam", "clog", "success rate"],
    "support_service": ["support", "customer service", "warranty", "rma", "snapmaker team"],
    "shipping_kickstarter": ["shipping", "kickstarter", "delivery", "ship", "backer", "pledge", "delay"],
    "multi_color": ["multi color", "multicolor", "multi-color", "4 color", "color change", "color swap"],
    "open_source": ["open source", "klipper", "gpl", "fluidd", "mainsail"],
    "quality_control": ["quality control", "qc", "defect", "scratch", "dent", "dust", "clicking sound", "loose panel"],
}

# --- 情感分析关键词 ---
POSITIVE_KW = [
    "love", "amazing", "excellent", "impressed", "game changer", "great",
    "best", "fantastic", "perfect", "recommend", "awesome", "happy",
    "beautiful", "clean", "solid", "reliable", "worth every penny",
    "no waste", "minimal waste", "fast swap", "quick change",
]

NEGATIVE_KW = [
    "issue", "problem", "bug", "fail", "disappoint", "frustrat",
    "noise", "loud", "crash", "error", "defect", "broken",
    "miss", "lack", "expensive", "overpriced", "regret", "return",
    "unreliable", "poor", "bad", "terrible", "waste of", "hate",
]

# --- 视频筛选 ---
MIN_VIEW_COUNT = 10_000      # 最低播放量
TOP_N_VIDEOS = 50            # 分析前 N 个视频

# --- LLM 配置（OpenAI 兼容接口，支持阿里云 Qwen / OpenAI / 其他兼容服务）---
# 通过环境变量覆盖：LLM_BASE_URL, LLM_MODEL
LLM_BASE_URL = os.environ.get(
    "LLM_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
LLM_MODEL_DEEP = os.environ.get("LLM_MODEL_DEEP", "qwen3.5-plus")    # 字幕分析（需要深度推理）
LLM_MODEL_FAST = os.environ.get("LLM_MODEL_FAST", "qwen-plus")       # 评论分析、综合报告（结构化提取）
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.3
LLM_RATE_LIMIT_DELAY = 2.5        # 每次调用间隔（秒），减少限流
LLM_MAX_RETRIES = 5               # 单次调用重试次数
LLM_RETRY_BASE_DELAY = 3.0        # 指数退避基础延迟（秒）
LLM_MAX_ROUNDS = 3                # Step 7 整体重试轮数
LLM_ROUND_WAIT_BASE = 30          # 轮间等待基数（秒）

# =====================================================================
# LLM Prompt 模板 — U1 评测
# =====================================================================
PROMPT_TRANSCRIPT_ANALYSIS = """你是一名专业的3D打印产品分析师。请仔细阅读以下YouTube评测视频的完整字幕文本，提取该视频中**所有与 Snapmaker U1 相关的内容**进行深度分析。

**关键要求**：
- 本视频可能是 Snapmaker U1 专题评测，也可能是多产品对比/年度盘点等综合视频
- 无论视频主题是什么，你的分析必须**聚焦于视频中对 Snapmaker U1 的评价**
- 所有"正面"、"负面"的判定，均指**对 Snapmaker U1 而言**的正面/负面
- 如果视频中对 U1 的提及很少，请如实说明，不要编造内容

视频标题: {title}
频道: {channel}
观看量: {view_count:,}
赞助状态: {sponsor_status}

字幕全文:
{transcript}

请用中文输出以下结构化分析，每一项都要详细、具体，引用原文中的关键表述（用括号标注英文原文）：

## 1. 视频概述与 U1 相关度
- 该视频的主题类型（U1 专题评测 / 多产品对比 / 年度盘点 / 其他）
- 视频中 Snapmaker U1 内容的大致占比（估算百分比）
- 如果是多产品视频，列出视频涉及的所有产品

## 2. 核心结论 (Core Conclusions)
该评测者**对 Snapmaker U1** 的总体评价是什么？给出明确的推荐/不推荐判定及理由。
如果评测者对多个产品进行了排名，请明确列出排名顺序和理由。

## 3. 对 Snapmaker U1 的优点评价 (Pros for U1)
逐条列出评测者提到的 **U1 的**优点，每条包含:
- 优点描述（中文）
- 原文关键表述（English original）
- 具体数据或对比（如有）

## 4. 对 Snapmaker U1 的缺点/问题 (Cons/Issues for U1)
逐条列出评测者提到的 **U1 的**缺点和问题，每条包含:
- 缺点描述（中文）
- 原文关键表述（English original）
- 严重程度评估（致命/重要/一般/轻微）

## 5. 对 Snapmaker U1 的改进建议 (Improvement Suggestions for U1)
评测者对 U1 明确提出或暗示的改进建议：
- 建议内容（中文）
- 原文依据（English original）

## 6. 与 Bambu Lab 的对比 (Bambu Lab Comparison)
**专门提取**视频中 Snapmaker U1 与 Bambu Lab 产品（H2C、P1S、X1C、A1 等）的所有对比内容：
- 对比了哪些 Bambu 产品？
- 逐维度列出对比结论（换色速度、废料量、打印质量、价格、噪音、可靠性等）
- 评测者的品牌偏好判定：更推荐 U1 还是 Bambu？理由是什么？
- 原文关键对比表述（English original）
- 如果没有与 Bambu 的对比，明确标注"本视频未涉及 Bambu 对比"

## 7. 与其他竞品的对比 (Other Competitor Comparisons)
如有与 Bambu 以外竞品（Prusa、Creality 等）的对比，列出：
- 对比对象、对比维度、结论

## 8. 关键数据点 (Key Data Points)
提取所有与 U1 相关的具体数值数据（打印速度、换头时间、废料重量、噪音、温度、价格等）。

## 9. 评测者品牌偏好总结 (Reviewer Brand Preference)
综合全视频内容，给出评测者的品牌/产品偏好排序（如有），并引用支撑该判断的原文。
"""

# =====================================================================
# LLM Prompt 模板 — H2C / Vortek 评测
# =====================================================================
PROMPT_TRANSCRIPT_ANALYSIS_H2C = """你是一名专业的3D打印产品分析师。请仔细阅读以下YouTube评测视频的完整字幕文本，提取该视频中**所有与 Bambu Lab H2C / Vortek 相关的内容**进行深度分析。

**关键要求**：
- 本视频可能是 Bambu Lab H2C / Vortek 专题评测，也可能是多产品对比/年度盘点等综合视频
- 无论视频主题是什么，你的分析必须**聚焦于视频中对 Bambu Lab H2C / Vortek 的评价**
- 所有"正面"、"负面"的判定，均指**对 Bambu Lab H2C / Vortek 而言**的正面/负面
- 如果视频中对 H2C / Vortek 的提及很少，请如实说明，不要编造内容

视频标题: {title}
频道: {channel}
观看量: {view_count:,}
赞助状态: {sponsor_status}

字幕全文:
{transcript}

请用中文输出以下结构化分析，每一项都要详细、具体，引用原文中的关键表述（用括号标注英文原文）：

## 1. 视频概述与 H2C 相关度
- 该视频的主题类型（H2C / Vortek 专题评测 / 多产品对比 / 年度盘点 / 其他）
- 视频中 Bambu Lab H2C / Vortek 内容的大致占比（估算百分比）
- 如果是多产品视频，列出视频涉及的所有产品

## 2. 核心结论 (Core Conclusions)
该评测者**对 Bambu Lab H2C / Vortek** 的总体评价是什么？给出明确的推荐/不推荐判定及理由。
如果评测者对多个产品进行了排名，请明确列出排名顺序和理由。

## 3. 对 H2C 的优点评价 (Pros for H2C / Vortek)
逐条列出评测者提到的 **H2C / Vortek 的**优点，每条包含:
- 优点描述（中文）
- 原文关键表述（English original）
- 具体数据或对比（如有）

## 4. 对 H2C 的缺点/问题 (Cons/Issues for H2C / Vortek)
逐条列出评测者提到的 **H2C / Vortek 的**缺点和问题，每条包含:
- 缺点描述（中文）
- 原文关键表述（English original）
- 严重程度评估（致命/重要/一般/轻微）

## 5. 对 H2C 的改进建议 (Improvement Suggestions for H2C / Vortek)
评测者对 H2C / Vortek 明确提出或暗示的改进建议：
- 建议内容（中文）
- 原文依据（English original）

## 6. 与 Snapmaker U1 的对比 (Snapmaker U1 Comparison)
**专门提取**视频中 Bambu Lab H2C / Vortek 与 Snapmaker U1 的所有对比内容：
- 是否直接对比了 Snapmaker U1？
- 逐维度列出对比结论（换色速度、废料量、打印质量、价格、噪音、可靠性等）
- 评测者的品牌偏好判定：更推荐 H2C 还是 U1？理由是什么？
- 原文关键对比表述（English original）
- 如果没有与 Snapmaker U1 的对比，明确标注"本视频未涉及 Snapmaker U1 对比"

## 7. 与其他竞品的对比 (Other Competitor Comparisons)
如有与 Snapmaker U1 以外竞品（Prusa、Creality 等）的对比，列出：
- 对比对象、对比维度、结论

## 8. 关键数据点 (Key Data Points)
提取所有与 H2C / Vortek 相关的具体数值数据（打印速度、换头时间、废料重量、噪音、温度、价格等）。

## 9. 评测者品牌偏好总结 (Reviewer Brand Preference)
综合全视频内容，给出评测者的品牌/产品偏好排序（如有），并引用支撑该判断的原文。
"""

# =====================================================================
# LLM Prompt 模板 — 综合对比评测
# =====================================================================
PROMPT_TRANSCRIPT_ANALYSIS_COMPARISON = """你是一名专业的3D打印产品分析师。请仔细阅读以下YouTube评测视频的完整字幕文本，该视频是一期**对比评测**，涉及 Snapmaker U1 和 Bambu Lab H2C（或其他竞品）的对比。请提取视频中**所有对比相关内容**进行深度分析。

**关键要求**：
- 本视频的核心是产品之间的对比，请同时分析对两款产品的评价
- 如果视频还涉及其他产品（Prusa、Creality 等），也需一并提取对比结论
- 所有"正面"、"负面"的判定，请分别标注是**对哪款产品**而言的
- 如果视频实际上不是对比视频，请如实说明

视频标题: {title}
频道: {channel}
观看量: {view_count:,}
赞助状态: {sponsor_status}

字幕全文:
{transcript}

请用中文输出以下结构化分析，每一项都要详细、具体，引用原文中的关键表述（用括号标注英文原文）：

## 1. 视频概述
- 该视频的对比类型（双产品直接对比 / 多产品横评 / 年度盘点 / 其他）
- 视频涉及的所有产品列表
- Snapmaker U1 内容占比（估算百分比）
- Bambu Lab H2C / Vortek 内容占比（估算百分比）

## 2. 核心对比结论 (Core Comparison Conclusions)
评测者在对比后得出的**最终结论**是什么？
- 整体推荐哪款产品？在什么场景下推荐？
- 是否有明确的胜负判定？还是"各有优劣"？
- 原文核心结论表述（English original）

## 3. 对 Snapmaker U1 的评价（优点/缺点）
逐条列出评测者在对比中提到的 **U1 的优点和缺点**，每条包含：
- 评价描述（中文）
- 原文关键表述（English original）
- 具体数据（如有）
- 判定为优点还是缺点

## 4. 对 Bambu H2C 的评价（优点/缺点）
逐条列出评测者在对比中提到的 **H2C / Vortek 的优点和缺点**，每条包含：
- 评价描述（中文）
- 原文关键表述（English original）
- 具体数据（如有）
- 判定为优点还是缺点

## 5. 逐维度对比（Dimension-by-Dimension Comparison）
按以下维度分别列出评测者的对比结论（如视频涉及），每个维度标注"U1 胜 / H2C 胜 / 平手 / 未涉及"：
- 打印速度（Print Speed）
- 废料/耗材浪费（Waste / Purge）
- 打印质量（Print Quality）
- 价格/性价比（Price / Value）
- 噪音水平（Noise Level）
- 可靠性/成功率（Reliability / Success Rate）
- 换色机制（Color Change Mechanism）
- 软件/固件体验（Software / Firmware）
- 构建体积（Build Volume）
- 多色打印效果（Multi-color Results）
- 易用性/开箱体验（Ease of Use / Setup）
- 外壳/密封性（Enclosure）
- 其他维度（如有）

## 6. 评测者最终推荐 (Final Recommendation)
- 评测者最终更推荐哪款产品？在什么使用场景下？
- 评测者认为哪类用户应该选择 U1？哪类应该选择 H2C？
- 原文推荐表述（English original）

## 7. 关键数据点 (Key Data Points)
提取视频中所有与对比相关的具体数值数据，按产品分组列出。

## 8. 品牌偏好总结 (Brand Preference Summary)
综合全视频内容，给出评测者的品牌/产品偏好排序，并引用支撑该判断的原文。
- 评测者是否有明显的品牌倾向？
- 该倾向是否影响了对比的客观性？
"""

# =====================================================================
# LLM Prompt 模板 — 评论分析（U1）
# =====================================================================
PROMPT_COMMENT_ANALYSIS = """你是一位用户反馈分析专家。请分析以下YouTube视频的用户评论，**只提取与 Snapmaker U1 相关的用户反馈**。

**关键要求**：
- 本视频可能主要讲 Bambu H2C 或其他产品，评论中大量内容可能与 U1 无关
- 你必须**只分析提到 Snapmaker / U1 / SnapSwap / 换头 的评论**
- 所有"正面"、"负面"的判定，必须是**针对 Snapmaker U1**的
- 如果一条评论同时讨论 U1 和 Bambu，请分别标注该评论对 U1 是正面还是负面
- 如果几乎没有评论提到 U1，请如实说明"本视频评论中与 U1 相关的讨论极少"

视频标题: {title}
频道: {channel}
总评论数量: {comment_count}

以下是按点赞数排序的用户评论:
{comments}

请用中文输出以下结构化分析（引用关键评论时在括号内保留英文原文）。

**数据支撑要求：** 所有结论必须给出具体数字，不要使用"普遍"、"公认"、"高频"等模糊表述。

## 1. U1 相关评论概况
- 总评论数 vs 提到 U1/Snapmaker 的评论数（给出具体数字和占比）
- 这些 U1 相关评论的整体情感倾向统计（正面 X 条、负面 X 条、中性 X 条）

## 2. 对 U1 的正面反馈 (Positive Feedback for U1)
逐个主题列出**用户对 U1 的**正面评价：
- 主题名称
- 提及该主题的评论数量和累计点赞数
- 2-3 条代表性高赞评论原文（含用户名和点赞数）

## 3. 对 U1 的负面反馈 (Negative Feedback for U1)
逐个主题列出**用户对 U1 的**负面评价：
- 主题名称
- 提及该主题的评论数量和累计点赞数
- 2-3 条代表性高赞评论原文（含用户名和点赞数）

## 4. 对 Bambu 的评论情感分析 (Bambu Sentiment in Comments)
**单独统计**评论中提到 Bambu / H2C / AMS 的评论：
- 总评论数 vs 提到 Bambu 的评论数（给出具体数字和占比）
- 这些 Bambu 相关评论的情感倾向统计（正面 X 条、负面 X 条、中性 X 条）
- 对 Bambu 的正面评价主题（逐主题列出，含评论数量和代表性引用）
- 对 Bambu 的负面评价主题（逐主题列出，含评论数量和代表性引用）

## 5. U1 vs Bambu 评论对比 (U1 vs Bambu Comment Comparison)
将上述 U1 评论分析和 Bambu 评论分析进行**直接对比**：
- U1 相关评论数 vs Bambu 相关评论数
- U1 正面比例 vs Bambu 正面比例
- U1 负面比例 vs Bambu 负面比例
- 用户在对比时偏好 U1 的数量 vs 偏好 Bambu 的数量
- 代表性对比评论原文（用户直接比较两个品牌的评论）

## 6. 用户对 U1 的建议和疑问
用户针对 U1 提出的改进建议和问题，标注数量。

## 7. 关键洞察 (Key Insights)
从评论数据中发现的重要信号，每条附数据支撑。
"""

# =====================================================================
# LLM Prompt 模板 — 评论分析（H2C / Vortek）
# =====================================================================
PROMPT_COMMENT_ANALYSIS_H2C = """你是一位用户反馈分析专家。请分析以下YouTube视频的用户评论，**只提取与 Bambu Lab H2C / Vortek 相关的用户反馈**。

**关键要求**：
- 本视频可能主要讲 Snapmaker U1 或其他产品，评论中大量内容可能与 H2C 无关
- 你必须**只分析提到 Bambu / H2C / H2D / Vortek / 换头 的评论**
- 所有"正面"、"负面"的判定，必须是**针对 Bambu Lab H2C / Vortek**的
- 如果一条评论同时讨论 H2C 和 Snapmaker，请分别标注该评论对 H2C 是正面还是负面
- 如果几乎没有评论提到 H2C，请如实说明"本视频评论中与 H2C 相关的讨论极少"

视频标题: {title}
频道: {channel}
总评论数量: {comment_count}

以下是按点赞数排序的用户评论:
{comments}

请用中文输出以下结构化分析（引用关键评论时在括号内保留英文原文）。

**数据支撑要求：** 所有结论必须给出具体数字，不要使用"普遍"、"公认"、"高频"等模糊表述。

## 1. H2C 相关评论概况
- 总评论数 vs 提到 H2C / Bambu / Vortek 的评论数（给出具体数字和占比）
- 这些 H2C 相关评论的整体情感倾向统计（正面 X 条、负面 X 条、中性 X 条）

## 2. 对 H2C 的正面反馈 (Positive Feedback for H2C / Vortek)
逐个主题列出**用户对 H2C 的**正面评价：
- 主题名称
- 提及该主题的评论数量和累计点赞数
- 2-3 条代表性高赞评论原文（含用户名和点赞数）

## 3. 对 H2C 的负面反馈 (Negative Feedback for H2C / Vortek)
逐个主题列出**用户对 H2C 的**负面评价：
- 主题名称
- 提及该主题的评论数量和累计点赞数
- 2-3 条代表性高赞评论原文（含用户名和点赞数）

## 4. 对 Snapmaker 的评论情感分析 (Snapmaker Sentiment in Comments)
**单独统计**评论中提到 Snapmaker / U1 / SnapSwap 的评论：
- 总评论数 vs 提到 Snapmaker 的评论数（给出具体数字和占比）
- 这些 Snapmaker 相关评论的情感倾向统计（正面 X 条、负面 X 条、中性 X 条）
- 对 Snapmaker 的正面评价主题（逐主题列出，含评论数量和代表性引用）
- 对 Snapmaker 的负面评价主题（逐主题列出，含评论数量和代表性引用）

## 5. H2C vs Snapmaker 评论对比 (H2C vs Snapmaker Comment Comparison)
将上述 H2C 评论分析和 Snapmaker 评论分析进行**直接对比**：
- H2C 相关评论数 vs Snapmaker 相关评论数
- H2C 正面比例 vs Snapmaker 正面比例
- H2C 负面比例 vs Snapmaker 负面比例
- 用户在对比时偏好 H2C 的数量 vs 偏好 Snapmaker 的数量
- 代表性对比评论原文（用户直接比较两个品牌的评论）

## 6. 用户对 H2C 的建议和疑问
用户针对 H2C / Vortek 提出的改进建议和问题，标注数量。

## 7. 关键洞察 (Key Insights)
从评论数据中发现的重要信号，每条附数据支撑。
"""

# =====================================================================
# LLM Prompt 模板 — 评论分析（综合对比）
# =====================================================================
PROMPT_COMMENT_ANALYSIS_COMPARISON = """你是一位用户反馈分析专家。请分析以下YouTube对比评测视频的用户评论，**同时提取与 Snapmaker U1 和 Bambu Lab H2C / Vortek 相关的用户反馈**，并进行品牌偏好对比。

**关键要求**：
- 本视频是对比评测，评论中可能同时讨论两款产品
- 你需要**分别统计**对 Snapmaker U1 和对 Bambu H2C 的评论
- 一条评论可能同时涉及两款产品，请分别标注对每款产品的情感倾向
- 重点关注用户在评论中**直接对比两款产品**的表述
- 所有结论必须给出具体数字

视频标题: {title}
频道: {channel}
总评论数量: {comment_count}

以下是按点赞数排序的用户评论:
{comments}

请用中文输出以下结构化分析（引用关键评论时在括号内保留英文原文）。

**数据支撑要求：** 所有结论必须给出具体数字，不要使用"普遍"、"公认"、"高频"等模糊表述。

## 1. 品牌相关评论概况（分别统计 U1 和 H2C 提及）
- 总评论数
- 提到 Snapmaker / U1 的评论数（具体数字和占比）
- 提到 Bambu / H2C / Vortek 的评论数（具体数字和占比）
- 同时提到两款产品的评论数（具体数字和占比）
- 仅讨论其他话题的评论数

## 2. 对 U1 的正面/负面反馈
逐个主题列出**用户对 U1 的**正面和负面评价：
- 正面主题：主题名称、评论数量、累计点赞数、2-3 条代表性评论原文（含用户名和点赞数）
- 负面主题：主题名称、评论数量、累计点赞数、2-3 条代表性评论原文（含用户名和点赞数）

## 3. 对 H2C 的正面/负面反馈
逐个主题列出**用户对 H2C / Vortek 的**正面和负面评价：
- 正面主题：主题名称、评论数量、累计点赞数、2-3 条代表性评论原文（含用户名和点赞数）
- 负面主题：主题名称、评论数量、累计点赞数、2-3 条代表性评论原文（含用户名和点赞数）

## 4. 品牌偏好对比（支持 U1 vs 支持 H2C 的评论数量）
**核心统计**：
- 明确表示偏好 U1 的评论数量和累计点赞数
- 明确表示偏好 H2C 的评论数量和累计点赞数
- 认为"各有优劣"的评论数量
- 偏好 U1 的代表性评论原文（2-3 条，含用户名和点赞数）
- 偏好 H2C 的代表性评论原文（2-3 条，含用户名和点赞数）
- 用户偏好的主要理由归纳

## 5. 用户建议和疑问
用户针对两款产品分别提出的改进建议和问题，按产品分组，标注数量。

## 6. 关键洞察 (Key Insights)
从评论数据中发现的重要信号，每条附数据支撑。特别关注：
- 用户群体的品牌偏好倾向
- 评论情感与视频评测结论是否一致
- 是否有明显的"粉丝站队"现象
"""

# =====================================================================
# LLM Prompt 模板 — 综合报告（U1）
# =====================================================================
PROMPT_OVERALL_REPORT = """你是一位资深3D打印行业分析师。基于对{video_count}个YouTube视频中关于 Snapmaker U1 的深度分析结果，请生成一份综合分析报告。

**关键要求**：
- 所有分析必须聚焦于 Snapmaker U1，正面/负面均指对 U1 而言
- 部分视频可能主要讲竞品（如 Bambu H2C），仅顺带提到 U1——这类视频的权重应较低
- 所有结论必须有数据支撑：标注 X/{video_count} 个视频、频道名列表
- 不能出现没有数字支撑的"普遍认为"、"大多数评测者表示"等表述

以下是每个视频的分析摘要（**这是本报告的核心数据来源**）:
{video_summaries}

以下是评论分析的汇总（**仅作补充参考，评论已过滤为 U1 相关**）:
{comment_summaries}

请用中文撰写一份结构完整的综合分析报告（关键术语和原始表述在括号内保留英文），包括:

## 1. 执行摘要 (Executive Summary)
300字以内的核心发现概述。包含关键统计数字（分析了多少视频、多少评测者推荐等）。

## 2. 整体口碑评估 (Overall Reputation Assessment)
- 评测者总体态度分布：明确推荐 X 个、有保留推荐 X 个、不推荐 X 个、未明确表态 X 个
- 列出每个视频的立场判定表格（频道名 | 视频类型 | 对U1的立场 | 核心理由）
- 按 U1 相关度分组：U1 专题评测 vs 多产品对比 vs 仅顺带提及

## 3. 优点/亮点统计 (Strengths Statistics)
汇总所有视频中评测者对 U1 的优点评价，按"被提及视频数"排序。
每项列出：
- 优点描述
- 提及该优点的视频数量及频道名列表（如：5/{video_count} 个视频 — A, B, C, D, E）
- 典型原文引用（英文，标注来源频道）
- 评论中的印证情况（简要，如有）

## 4. 缺点/问题统计 (Issues Statistics)
汇总所有视频中评测者对 U1 的缺点评价，按"被提及视频数"排序。
每项列出：
- 问题描述
- 提及该问题的视频数量及频道名列表
- 典型原文引用（英文，标注来源频道）
- 严重程度评估（致命/重要/一般/轻微）
- 评论中的印证情况（简要，如有）

## 5. Snapmaker U1 vs Bambu Lab 深度对比 (U1 vs Bambu Lab)
**专门汇总**所有视频中 U1 与 Bambu 产品的对比：
- 哪些视频进行了直接对比？列出频道名
- 逐维度汇总对比结论（换色速度、废料、质量、价格、噪音、可靠性等）
- 评测者的品牌偏好统计：偏好 U1 的 X 个（频道名）、偏好 Bambu 的 X 个（频道名）、各有优劣的 X 个（频道名）
- 用户评论中的品牌偏好补充

## 6. 核心改进方向 (Improvement Priorities)
基于缺点统计，按优先级排序的改进建议。每条标注数据来源。

## 7. 评测者观点一致性与分歧 (Consensus vs Disagreements)
- 一致观点：X/{video_count} 个视频持相同看法的议题，列出频道名
- 分歧观点：不同评测者看法相反的议题，分别列出正反双方频道名及论据

## 8. 市场机会与风险 (Market Opportunities & Risks)
基于分析的战略洞察，每条附数据支撑。
"""

PROMPT_OVERALL_REPORT_U1 = PROMPT_OVERALL_REPORT

# =====================================================================
# LLM Prompt 模板 — 元数据分析（无字幕视频，U1）
# =====================================================================
PROMPT_METADATA_ANALYSIS = """你是一名专业的3D打印产品分析师。以下YouTube视频**没有可用字幕**，请基于视频标题、描述、标签和用户评论进行分析，提取**所有与 Snapmaker U1 相关的信息**。

**关键要求**：
- 本分析基于元数据和评论，而非视频字幕内容，请在分析中明确标注数据来源
- 区分"标题/描述直接提供的信息"和"从评论中推断的信息"
- 不要编造视频中可能说了什么，只分析已有的文本数据
- 如果信息不足，请如实说明，不要过度推断

视频标题: {title}
频道: {channel}
观看量: {view_count:,}
赞助状态: {sponsor_status}
视频时长: {duration}
视频描述:
{description}

视频标签: {tags}

频道信息: 粉丝数 {subscriber_count}, {channel_description}

用户评论（按点赞数排序，前50条）:
{comments}

请用中文输出以下结构化分析，明确标注每条信息的来源（标题/描述/标签/评论）：

## 1. 视频概述与 U1 相关度
- 根据标题和描述判断视频主题类型
- 估算该视频与 Snapmaker U1 的相关度
- 来源标注：[标题] / [描述] / [标签]

## 2. 从标题/描述提取的关键信息
- 视频主题和定位
- 提到的具体产品、功能、参数
- 赞助/合作声明（如有）

## 3. 从用户评论推断的视频内容要点
- 评论中反复讨论的话题（标注评论数量）
- 用户对视频内容的反馈和补充
- 用户提到的 U1 优缺点（标注来源为评论）

## 4. 对 Snapmaker U1 的评价汇总
- 正面评价（标注来源和数量）
- 负面评价/问题（标注来源和数量）

## 5. 与竞品的对比信息
- 评论中与 Bambu Lab / 其他竞品的对比（如有）

## 6. 分析局限性
- 本分析基于元数据和评论，无法获取视频实际演示内容
- 列出无法确认的关键问题
"""

# =====================================================================
# LLM Prompt 模板 — 元数据分析（无字幕视频，H2C）
# =====================================================================
PROMPT_METADATA_ANALYSIS_H2C = """你是一名专业的3D打印产品分析师。以下YouTube视频**没有可用字幕**，请基于视频标题、描述、标签和用户评论进行分析，提取**所有与 Bambu Lab H2C / Vortek 相关的信息**。

**关键要求**：
- 本分析基于元数据和评论，而非视频字幕内容，请在分析中明确标注数据来源
- 区分"标题/描述直接提供的信息"和"从评论中推断的信息"
- 不要编造视频中可能说了什么，只分析已有的文本数据
- 如果信息不足，请如实说明，不要过度推断

视频标题: {title}
频道: {channel}
观看量: {view_count:,}
赞助状态: {sponsor_status}
视频时长: {duration}
视频描述:
{description}

视频标签: {tags}

频道信息: 粉丝数 {subscriber_count}, {channel_description}

用户评论（按点赞数排序，前50条）:
{comments}

请用中文输出以下结构化分析，明确标注每条信息的来源（标题/描述/标签/评论）：

## 1. 视频概述与 H2C 相关度
- 根据标题和描述判断视频主题类型
- 估算该视频与 Bambu Lab H2C / Vortek 的相关度
- 来源标注：[标题] / [描述] / [标签]

## 2. 从标题/描述提取的关键信息
- 视频主题和定位
- 提到的具体产品、功能、参数
- 赞助/合作声明（如有）

## 3. 从用户评论推断的视频内容要点
- 评论中反复讨论的话题（标注评论数量）
- 用户对视频内容的反馈和补充
- 用户提到的 H2C 优缺点（标注来源为评论）

## 4. 对 Bambu Lab H2C / Vortek 的评价汇总
- 正面评价（标注来源和数量）
- 负面评价/问题（标注来源和数量）

## 5. 与竞品的对比信息
- 评论中与 Snapmaker U1 / 其他竞品的对比（如有）

## 6. 分析局限性
- 本分析基于元数据和评论，无法获取视频实际演示内容
- 列出无法确认的关键问题
"""

# =====================================================================
# LLM Prompt 模板 — 元数据分析（无字幕视频，综合对比）
# =====================================================================
PROMPT_METADATA_ANALYSIS_COMPARISON = """你是一名专业的3D打印产品分析师。以下YouTube视频**没有可用字幕**，请基于视频标题、描述、标签和用户评论进行分析，提取**所有与 Snapmaker U1 和 Bambu Lab H2C 对比相关的信息**。

**关键要求**：
- 本分析基于元数据和评论，而非视频字幕内容，请在分析中明确标注数据来源
- 区分"标题/描述直接提供的信息"和"从评论中推断的信息"
- 不要编造视频中可能说了什么，只分析已有的文本数据
- 如果信息不足，请如实说明，不要过度推断

视频标题: {title}
频道: {channel}
观看量: {view_count:,}
赞助状态: {sponsor_status}
视频时长: {duration}
视频描述:
{description}

视频标签: {tags}

频道信息: 粉丝数 {subscriber_count}, {channel_description}

用户评论（按点赞数排序，前50条）:
{comments}

请用中文输出以下结构化分析，明确标注每条信息的来源（标题/描述/标签/评论）：

## 1. 视频概述与对比相关度
- 根据标题和描述判断视频主题类型（直接对比 / 综合评测 / 其他）
- 涉及的产品列表
- 来源标注：[标题] / [描述] / [标签]

## 2. 从标题/描述提取的关键信息
- 视频主题和定位
- 提到的具体产品、功能、参数
- 赞助/合作声明（如有）

## 3. 从用户评论推断的对比要点
- 评论中反复讨论的对比话题（标注评论数量）
- 用户对 U1 的评价（正面/负面，标注数量）
- 用户对 H2C 的评价（正面/负面，标注数量）
- 用户的品牌偏好倾向（标注数量）

## 4. 对比评价汇总
- U1 优势（来源标注）
- H2C 优势（来源标注）
- 评论中的品牌偏好统计

## 5. 分析局限性
- 本分析基于元数据和评论，无法获取视频实际演示和对比内容
- 列出无法确认的关键问题
"""

# =====================================================================
# LLM Prompt 模板 — 综合报告（H2C / Vortek）
# =====================================================================
PROMPT_OVERALL_REPORT_H2C = """你是一位资深3D打印行业分析师。基于对{video_count}个YouTube视频中关于 Bambu Lab H2C / Vortek 的深度分析结果，请生成一份综合分析报告。

**关键要求**：
- 所有分析必须聚焦于 Bambu Lab H2C / Vortek，正面/负面均指对 H2C / Vortek 而言
- 部分视频可能主要讲竞品（如 Snapmaker U1），仅顺带提到 H2C——这类视频的权重应较低
- 所有结论必须有数据支撑：标注 X/{video_count} 个视频、频道名列表
- 不能出现没有数字支撑的"普遍认为"、"大多数评测者表示"等表述

以下是每个视频的分析摘要（**这是本报告的核心数据来源**）:
{video_summaries}

以下是评论分析的汇总（**仅作补充参考，评论已过滤为 H2C 相关**）:
{comment_summaries}

请用中文撰写一份结构完整的综合分析报告（关键术语和原始表述在括号内保留英文），包括:

## 1. 执行摘要 (Executive Summary)
300字以内的核心发现概述。包含关键统计数字（分析了多少视频、多少评测者推荐等）。

## 2. 整体口碑评估 (Overall Reputation Assessment)
- 评测者总体态度分布：明确推荐 X 个、有保留推荐 X 个、不推荐 X 个、未明确表态 X 个
- 列出每个视频的立场判定表格（频道名 | 视频类型 | 对 H2C 的立场 | 核心理由）
- 按 H2C 相关度分组：H2C 专题评测 vs 多产品对比 vs 仅顺带提及

## 3. 优点/亮点统计 (Strengths Statistics)
汇总所有视频中评测者对 H2C / Vortek 的优点评价，按"被提及视频数"排序。
每项列出：
- 优点描述
- 提及该优点的视频数量及频道名列表（如：5/{video_count} 个视频 — A, B, C, D, E）
- 典型原文引用（英文，标注来源频道）
- 评论中的印证情况（简要，如有）

## 4. 缺点/问题统计 (Issues Statistics)
汇总所有视频中评测者对 H2C / Vortek 的缺点评价，按"被提及视频数"排序。
每项列出：
- 问题描述
- 提及该问题的视频数量及频道名列表
- 典型原文引用（英文，标注来源频道）
- 严重程度评估（致命/重要/一般/轻微）
- 评论中的印证情况（简要，如有）

## 5. Bambu H2C vs Snapmaker U1 深度对比 (H2C vs Snapmaker U1)
**专门汇总**所有视频中 H2C 与 Snapmaker U1 的对比：
- 哪些视频进行了直接对比？列出频道名
- 逐维度汇总对比结论（换色速度、废料、质量、价格、噪音、可靠性等）
- 评测者的品牌偏好统计：偏好 H2C 的 X 个（频道名）、偏好 U1 的 X 个（频道名）、各有优劣的 X 个（频道名）
- 用户评论中的品牌偏好补充

## 6. 核心改进方向 (Improvement Priorities)
基于缺点统计，按优先级排序的改进建议。每条标注数据来源。

## 7. 评测者观点一致性与分歧 (Consensus vs Disagreements)
- 一致观点：X/{video_count} 个视频持相同看法的议题，列出频道名
- 分歧观点：不同评测者看法相反的议题，分别列出正反双方频道名及论据

## 8. 市场机会与风险 (Market Opportunities & Risks)
基于分析的战略洞察，每条附数据支撑。重点分析 H2C / Vortek 在市场中的竞争地位和潜在风险。
"""

# =====================================================================
# LLM Prompt 模板 — 综合报告（对比）
# =====================================================================
PROMPT_OVERALL_REPORT_COMPARISON = """你是一位资深3D打印行业分析师。基于对{video_count}个YouTube对比评测视频的深度分析结果，请生成一份 Snapmaker U1 与 Bambu Lab H2C / Vortek 的综合对比分析报告。

**关键要求**：
- 本报告的核心是**双产品对比**，需要同时分析两款产品的市场表现
- 所有结论必须有数据支撑：标注 X/{video_count} 个视频、频道名列表
- 不能出现没有数字支撑的"普遍认为"、"大多数评测者表示"等表述
- 需要明确给出评测者群体的整体品牌偏好倾向

以下是每个视频的分析摘要（**这是本报告的核心数据来源**）:
{video_summaries}

以下是评论分析的汇总（**仅作补充参考**）:
{comment_summaries}

请用中文撰写一份结构完整的综合对比分析报告（关键术语和原始表述在括号内保留英文），包括:

## 1. 执行摘要 (Executive Summary)
300字以内的核心发现概述。包含关键统计数字（分析了多少对比视频、评测者整体偏好倾向等）。

## 2. 评测者推荐倾向总览 (Reviewer Recommendation Overview)
- 评测者总体推荐分布：推荐 U1 的 X 个、推荐 H2C 的 X 个、认为各有优劣的 X 个、未明确表态的 X 个
- 列出每个视频的推荐判定表格（频道名 | 对比类型 | 推荐产品 | 核心理由）
- 评测者群体的整体品牌倾向分析

## 3. Snapmaker U1 综合评价 (U1 Overall Assessment)
从所有对比视频中汇总评测者对 U1 的评价：
- U1 的核心优势（按被提及次数排序，每项标注频道名列表）
- U1 的核心劣势（按被提及次数排序，每项标注频道名列表）
- 评测者认为 U1 适合的用户群体

## 4. Bambu H2C 综合评价 (H2C Overall Assessment)
从所有对比视频中汇总评测者对 H2C / Vortek 的评价：
- H2C 的核心优势（按被提及次数排序，每项标注频道名列表）
- H2C 的核心劣势（按被提及次数排序，每项标注频道名列表）
- 评测者认为 H2C 适合的用户群体

## 5. 逐维度对比汇总 (Dimension-by-Dimension Comparison Summary)
按以下维度汇总所有视频的对比结论，每个维度标注评测者判定统计：
- 打印速度：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个（列出频道名）
- 废料/耗材浪费：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 打印质量：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 价格/性价比：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 噪音水平：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 可靠性/成功率：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 换色机制：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 软件/固件：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 易用性：U1 胜 X 个 / H2C 胜 X 个 / 平手 X 个
- 其他维度（如有）

## 6. 关键数据点对比 (Key Data Points Comparison)
汇总所有视频中的具体数值数据，按维度分组，直接对比两款产品的数据表现。

## 7. 用户评论中的品牌偏好 (User Comment Brand Preferences)
汇总所有对比视频评论中的品牌偏好数据：
- 评论中偏好 U1 的总数 vs 偏好 H2C 的总数
- 用户偏好 U1 的主要理由
- 用户偏好 H2C 的主要理由
- 评论情感与评测者结论的一致性分析

## 8. 评测者观点一致性与分歧 (Consensus vs Disagreements)
- 一致观点：X/{video_count} 个视频持相同看法的议题
- 分歧观点：不同评测者看法相反的议题，分别列出正反双方频道名及论据

## 9. 战略洞察与建议 (Strategic Insights & Recommendations)
基于对比分析的战略洞察：
- Snapmaker U1 的竞争优势和需要改进的方向
- Bambu H2C 的竞争优势和潜在弱点
- 市场机会与风险分析
- 每条附数据支撑
"""
