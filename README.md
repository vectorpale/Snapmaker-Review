# Snapmaker U1 用户反馈分析项目

基于多平台用户反馈数据，对 Snapmaker U1 3D 打印机进行深度分析，输出专业的分析报告。

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
| **Facebook** | `facebook/` | ✅ 已完成 | Snapmaker U1 Official Group 帖子与评论分析，生成 PPTX 报告 |
| **Forum** | `forum/` | ✅ 已完成 | Snapmaker 官方论坛 96 条帖子提取与分类分析 |
| **YouTube** | `youtube/` | 🔲 待开发 | YouTube 视频评论采集与分析 |
| **Reddit** | `reddit/` | 🔲 待开发 | Reddit 相关 subreddit 帖子分析 |

## 各模块说明

### Facebook (`facebook/`)

基于关键词 + 正则的多标签分类引擎，支持中英文，含情感分析和 PPTX 报告生成。

```bash
cd facebook/
pip install -r requirements.txt
python analyze.py <input.json>
```

### Forum (`forum/`)

从 Snapmaker 官方 Discourse 论坛提取数据，进行问题分类和功能请求提取。

```bash
cd forum/
pip install requests pandas openpyxl
python forum_extraction.py
```

## 分类体系

所有数据源使用统一的分类体系：

| 代码 | 类别 | 子类数 |
|------|------|--------|
| H | Hardware 硬件问题 | 17 |
| S | Software 软件问题 | 12 |
| M | Material 耗材相关 | 7 |
| U | User Experience 用户体验 | 12 |
| P | Positive 正面反馈 | 7 |
| O | Other 其他 | 4 |
