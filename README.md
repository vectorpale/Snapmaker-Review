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
| **Facebook** | `facebook/` | ✅ 已完成 | Snapmaker U1 Official Group 帖子分析，MECE 五分类 + LLM 子分类 |
| **Forum** | `forum/` | ✅ 已完成 | Snapmaker 官方论坛 96 条帖子提取与分类分析 |
| **YouTube** | `youtube/` | 🔲 待开发 | YouTube 视频评论采集与分析 |
| **Reddit** | `reddit/` | 🔲 待开发 | Reddit 相关 subreddit 帖子分析 |

## 核心分类体系（MECE 原则）

所有数据源使用统一的 MECE（互斥且完全穷尽）分类体系：

### 主贴五分类（第一层）

每个帖子有且仅归入1个类别，总数 = 样本总数。

| 序号 | 分类 | 英文 | 说明 |
|------|------|------|------|
| 1 | 问题/求助 | Questions / Help | 遇到问题、报告故障、寻求技术支持 |
| 2 | 打印结果展示/晒作品 | Print Showcase | 展示3D打印成品、分享作品 |
| 3 | 正面评价 | Positive Reviews | 对产品/服务表达赞赏 |
| 4 | 负面评价 | Negative Reviews | 对产品/服务表达不满 |
| 5 | 无意义 | Irrelevant | 不相关内容 |

### 子分类（第二层）

在每个主分类内部，帖子进一步归入1个子类别。详见各模块 README。

## 各模块说明

### Facebook (`facebook/`)

支持关键词规则 + Qwen LLM 增强的双模式分类，含情感分析和 PPTX 报告生成。

```bash
cd facebook/
pip install -r requirements.txt

# 关键词模式
python analyze.py <input.json>

# LLM 增强模式（需配置 .env）
python analyze.py <input.json> --llm
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
