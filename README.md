# Snapmaker U1 用户反馈分析项目

基于多平台用户反馈数据，对 Snapmaker U1 3D 打印机进行深度分析，输出专业的 PPTX 分析报告。

## 项目结构

```
Snapmaker-Review/
├── facebook/      # Facebook 数据源（Snapmaker U1 Official Group）
├── forum/         # 论坛数据源（Snapmaker 官方 Discourse 论坛）
├── youtube/       # YouTube 数据源（待开发）
├── reddit/        # Reddit 数据源（待开发）
└── README.md
```

## 数据源

| 数据源 | 目录 | 状态 | 说明 |
|--------|------|------|------|
| **Facebook** | `facebook/` | ✅ 已完成 | Snapmaker U1 Official Group 帖子分析，双维度分类 + LLM 子分类 |
| **Forum** | `forum/` | ✅ 已完成 | Snapmaker 官方论坛 96 条帖子提取与分类分析 |
| **YouTube** | `youtube/` | 🔲 待开发 | YouTube 视频评论采集与分析 |
| **Reddit** | `reddit/` | 🔲 待开发 | Reddit 相关 subreddit 帖子分析 |

## 核心分类体系（双维度）

### 维度一：内容类型（MECE）

每个帖子有且仅归入1个类别。

| 分类 | 英文 | 说明 |
|------|------|------|
| 问题/求助 | Questions / Help | 用户遇到具体问题，核心目的是寻求解决方案 |
| 评价/反馈 | Reviews / Feedback | 用户对产品/服务发表评价意见 |
| 产品展示 | Product Showcase | 展示打印成品照片/视频 |
| 其他 | Other | 无法归入以上类别的内容 |

### 维度二：情感倾向

每个帖子有且仅归入1个情感标签，独立于内容类型。

| 标签 | 英文 | 说明 |
|------|------|------|
| 正面 | Positive | 满意、赞赏、推荐 |
| 负面 | Negative | 不满、失望、抱怨 |
| 中性 | Neutral | 无明显情感倾向 |

### 子分类

- **正面反馈**（情感=正面）：多标签，每帖1-3个，总数可超过帖子数
- **负面反馈**（情感=负面）：多标签，每帖1-3个，总数可超过帖子数
- **问题/求助**（内容类型=问题/求助）：MECE 单标签，总数 = 帖子数
- LLM 可根据实际数据自适应调整子类别

详见各模块 README。

## 各模块说明

### Facebook (`facebook/`)

默认使用 Qwen LLM 分类（需配置 .env），含情感分析和 PPTX 报告生成。

```bash
cd facebook/
pip install -r requirements.txt

# 默认使用 LLM（需配置 .env 中的 QWEN_API_KEY）
python analyze.py <input.json>

# 禁用 LLM，仅用关键词规则分类
python analyze.py <input.json> --no-llm
```

### Forum (`forum/`)

从 Snapmaker 官方 Discourse 论坛提取数据，进行问题分类和功能请求提取。

```bash
cd forum/
pip install requests pandas openpyxl
python forum_extraction.py
```

## 报告规范

- **输出语言**：简体中文，英文原文以括号标注
- **中文字体**：等线 (DengXian)
- **英文字体**：Calibri
- **图表类型**：饼图、条形图（matplotlib 生成）
- **用户原声**：保留英文原文作为佐证
