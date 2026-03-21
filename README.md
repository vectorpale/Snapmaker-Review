# Snapmaker U1 YouTube 用户反馈分析系统

系统性搜集 Snapmaker U1 3D 打印机在 YouTube 上的评测视频与用户评论，使用 LLM 进行深度分析，生成产品反馈报告。

## 项目结构

```
├── youtube/          # V1：基础分析管道（通用搜索 + 简单分析）
├── youtube_u1/       # V2：U1 聚焦版（U1 专题 + Bambu 对比 + PPTX 输出）
├── youtube_multi/    # V3：多板块综合版（U1 评测 + H2C 评测 + 综合对比，三板块分析）
├── requirements.txt  # Python 依赖
└── .env              # API Keys（需自行创建）
```

### 版本对比

| 特性 | youtube/ (V1) | youtube_u1/ (V2) | youtube_multi/ (V3) |
|---|---|---|---|
| 视频数量 | Top 20 | Top 30 | Top N（可配置） |
| 搜索范围 | U1 相关 | U1 相关 | U1 + H2C/Vortek + 综合对比 |
| 视频分类 | 无 | 无 | 自动分为 U1 评测 / H2C 评测 / 综合对比 |
| LLM 模型 | qwen-plus | qwen3.5-plus | qwen3.5-plus（深度）+ qwen-plus（快速） |
| 分析聚焦 | 通用分析 | U1 聚焦 | 按类别分板块分析 |
| Bambu 对比 | 通用竞品章节 | 专属 Bambu 对比章节 | H2C 独立板块 + U1 vs H2C 对比 |
| 赞助检测 | 无 | 基础检测 | 多维度赞助/样机/自购检测 |
| 综合报告 | 单篇 | 单篇 | 三板块（U1 / H2C / 对比）分类汇总 |
| PowerPoint | 无 | 自动生成 | McKinsey 风格 PPTX + 图表 |
| Excel | 无 | 无 | 数据分析报告（多 Sheet） |
| PDF | 无 | 无 | Markdown 转 PDF |

## 环境配置

### 1. 创建 `.env` 文件

```bash
# YouTube Data API v3 Key
YOUTUBE_API_KEY=your_youtube_api_key

# LLM API Key（阿里云百炼 / DashScope）
LLM_API_KEY=your_dashscope_api_key

# 可选：代理配置
# HTTPS_PROXY=http://127.0.0.1:7890

# 可选：覆盖 LLM 配置
# LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# LLM_MODEL=qwen3.5-plus
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
# 推荐使用最新版本（V3 多板块综合分析）
cd youtube_multi
python main.py
```

### 执行流程（youtube_multi/ V3）

| Step | 说明 | 检查点文件 |
|---|---|---|
| 1 | YouTube 搜索视频（U1 + H2C + 对比关键词） | `data/search_results.json` |
| 2 | 获取视频详情 + 频道画像 + 赞助检测 | `data/video_details.json` |
| 3 | 视频转录提取（YouTube API + yt-dlp 双源） | `data/transcripts.json` |
| 4 | 关键词内容分析（补充数据） | `data/video_content_analysis.json` |
| 5 | 获取用户评论 | `data/all_comments.json` |
| 6 | 评论基础分析（情感 + 话题标注） | `data/comments_analyzed.csv` |
| 7 | LLM 深度分析（逐视频字幕 + 评论分析） | `data/llm_analysis.json` |
| 8 | 生成单视频详情报告 | `reports/per_video/*.md` |
| 9 | 生成总体报告（三板块 LLM 综合分析） | `reports/overall_*.md` |
| 10 | 生成 PowerPoint 产品分析报告 | `reports/snapmaker_u1_feedback_report.pptx` |
| 11 | 生成 Excel 数据分析报告 | `reports/snapmaker_u1_data_report.xlsx` |

### 断点续跑

每个 Step 都有 checkpoint 文件。如果中途中断，重新运行会自动跳过已完成的步骤。

如需强制重跑某个步骤，删除对应的 checkpoint 文件即可：
- 重跑 LLM 分析：删除 `data/llm_analysis.json`
- 重跑综合报告：删除 `data/overall_llm_analysis_u1.json` 等
- 重跑搜索：删除 `data/search_results.json`

## 分析特点（youtube_multi/ V3）

### 三板块分类分析
- **U1 评测板块**：Snapmaker U1 专题评测视频，聚焦产品优缺点
- **H2C/Vortek 评测板块**：Bambu Lab H2C 专题评测视频，了解竞品口碑
- **综合对比板块**：同时涉及 U1 和 H2C 的对比评测，提取头对头比较
- 自动分类：基于视频标题、描述、字幕中的关键词匹配

### 赞助/样机检测
- 多维度检测：明确赞助、样机提供、联盟链接、自购声明
- 正则模式匹配视频描述和字幕中的声明
- 为每个视频标注赞助状态和置信度

### U1 聚焦分析
- 所有"正面/负面"判定均针对 Snapmaker U1
- 评论只统计提到 U1/Snapmaker 的评论
- 多品牌视频会标注 U1 内容占比和品牌偏好排序

### Bambu Lab 对比
- H2C 独立板块分析，全面了解竞品评价
- 综合对比板块提取 U1 vs H2C 的直接比较
- 提供 U1 评论 vs Bambu 评论的情感数据对比

### 数据支撑要求
- 所有结论标注具体视频数/频道名/评论数
- 禁止使用"普遍认为"等模糊表述
- 要求提供代表性原文引用（含英文原文）

## 输出报告

- **Markdown 综合报告** — 三板块分类文本报告（U1 / H2C / 对比）
- **PowerPoint 报告** — McKinsey 风格演示文稿（含图表、数据概览、视频表格）
- **Excel 数据报告** — 多 Sheet 数据分析（视频列表、评论数据、统计汇总）
- **PDF 报告** — Markdown 转 PDF 输出
- **单视频详情报告** — 每个视频的独立分析（Markdown）
