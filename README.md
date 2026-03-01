# Snapmaker U1 YouTube 用户反馈分析系统

系统性搜集 Snapmaker U1 3D 打印机在 YouTube 上的评测视频与用户评论，使用 LLM 进行深度分析，生成产品反馈报告。

## 项目结构

```
├── youtube/          # 原始版本（基础分析管道）
├── youtube_u1/       # 增强版本（U1 聚焦 + Bambu 对比 + PPTX 输出）
├── requirements.txt  # Python 依赖
└── .env              # API Keys（需自行创建）
```

### `youtube/` vs `youtube_u1/` 区别

| 特性 | youtube/ | youtube_u1/ |
|---|---|---|
| 视频数量 | Top 20 | Top 30 |
| LLM 模型 | qwen-plus | qwen3.5-plus |
| 分析聚焦 | 通用分析 | 所有正面/负面聚焦 U1 |
| Bambu 对比 | 通用竞品章节 | 专属 Bambu 对比章节（视频+评论） |
| 评论过滤 | 所有评论 | 只统计 U1 相关评论 |
| 数据支撑 | 定性描述 | 要求具体数量/占比/频道名 |
| PDF | xhtml2pdf（字体有问题） | WeasyPrint（中文支持好） |
| PowerPoint | 无 | 自动生成 PPTX 报告 |
| LLM 超时 | 默认超时 | 600s 超时 + 16K 输出 tokens |

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
pip install weasyprint python-pptx  # youtube_u1/ 额外需要
```

## 运行

```bash
# 使用增强版本
cd youtube_u1
python main.py
```

### 执行流程

| Step | 说明 | 检查点文件 |
|---|---|---|
| 1 | YouTube 搜索视频 | `data/search_results.json` |
| 2 | 获取视频详情 + 频道画像 | `data/video_details.json` |
| 3 | 提取视频字幕 | `data/transcripts.json` |
| 4 | 关键词内容分析 | `data/video_content_analysis.json` |
| 5 | 获取用户评论 | `data/all_comments.json` |
| 6 | 评论基础分析 | `data/comments_analyzed.csv` |
| 7 | LLM 深度分析 | `data/llm_analysis.json` |
| 8 | 生成单视频报告 | `reports/per_video/*.md` |
| 9 | 生成综合报告 | `reports/youtube_analysis_report.md` |
| 10 | 生成 PDF 报告 | `reports/snapmaker_u1_feedback_report.pdf` |
| 11 | 生成 PowerPoint 报告 | `reports/snapmaker_u1_feedback_report.pptx` |

### 断点续跑

每个 Step 都有 checkpoint 文件。如果中途中断，重新运行会自动跳过已完成的步骤。

如需强制重跑某个步骤，删除对应的 checkpoint 文件即可：
- 重跑 LLM 分析：删除 `data/llm_analysis.json`
- 重跑搜索：删除 `data/search_results.json`

## 分析特点（youtube_u1/ 增强版）

### U1 聚焦分析
- 所有"正面/负面"判定均针对 Snapmaker U1
- 评论只统计提到 U1/Snapmaker 的评论
- 多品牌视频会标注 U1 内容占比和品牌偏好排序

### Bambu Lab 对比
- 每个视频报告都有专属"Bambu 对比"章节
- 评论分析中单独统计 Bambu 相关评论的情感
- 综合报告中有"U1 vs Bambu 深度对比"章节
- 提供 U1 评论 vs Bambu 评论的数据对比

### 数据支撑要求
- 所有结论标注具体视频数/频道名/评论数
- 禁止使用"普遍认为"等模糊表述
- 要求提供代表性原文引用（含英文原文）

## 输出报告

- **Markdown 综合报告** — 最完整的文本报告
- **PDF 报告** — 适合打印和分享，含图表
- **PowerPoint 报告** — 适合汇报演示
- **单视频详情报告** — 每个视频的独立分析（Markdown）
