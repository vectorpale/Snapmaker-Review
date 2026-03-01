"""
Snapmaker U1 YouTube 反馈提取系统 — 配置常量

所有搜索词、已知频道、正则模式、主题关键词均在此定义。
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
SEARCH_QUERIES = [
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

KNOWN_CHANNEL_NAMES = [r["channel"].lower() for r in KNOWN_REVIEWERS]

# --- 相关性过滤 ---
RELEVANCE_KEYWORDS = ["snapmaker", "u1", "snap maker"]

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
TOP_N_VIDEOS = 30            # 分析前 N 个视频

# --- LLM 配置（OpenAI 兼容接口，支持阿里云 Qwen / OpenAI / 其他兼容服务）---
# 通过环境变量覆盖：LLM_BASE_URL, LLM_MODEL
LLM_BASE_URL = os.environ.get(
    "LLM_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5-plus")
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.3
LLM_RATE_LIMIT_DELAY = 1.5        # 每次调用间隔（秒）
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 2.0        # 指数退避基础延迟

# --- LLM Prompt 模板 ---
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
