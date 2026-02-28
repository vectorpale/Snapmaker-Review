# 从零到一运行 Snapmaker U1 论坛提取程序 — 教学指南

## Context（背景）

你有一个 Python 脚本 `forum/forum_extraction.py`，它的作用是：
- 从 Snapmaker U1 官方论坛收集的 96 个帖子数据（已内置在脚本中）
- 自动分类帖子类型（问题、求助、功能建议、展示等）
- 分析高频问题主题、官方回应情况、错误码
- 生成 Markdown 报告 + JSON 数据 + Excel 汇总表

数据已经硬编码在脚本里（因为直接访问论坛 API 被网络代理拦截），所以**运行这个脚本不需要联网**。

---

## 第一步：检查 Python 环境

```bash
# 确认 Python 已安装（需要 3.6 以上版本）
python3 --version
```

期望输出类似：`Python 3.11.14`

如果没有 Python，需要先安装：
- **Mac**: `brew install python3`
- **Windows**: 从 [python.org](https://www.python.org/downloads/) 下载安装
- **Linux**: `sudo apt install python3 python3-pip`

---

## 第二步：安装依赖包

脚本需要两个第三方库：

```bash
# pandas: 数据处理和表格操作
# openpyxl: 生成 Excel 文件
pip install pandas openpyxl
```

> 如果报权限错误，加 `--user` 或 `--break-system-packages`：
> ```bash
> pip install pandas openpyxl --user
> ```

验证安装成功：
```bash
python3 -c "import pandas; import openpyxl; print('OK')"
```

---

## 第三步：进入项目目录

```bash
cd /path/to/Snapmaker-Review
```

确认文件存在：
```bash
ls -la forum/
# 应该看到：
#   forum_extraction.py   ← 主脚本
#   data/                 ← 输出数据目录
#   reports/              ← 输出报告目录
```

---

## 第四步：运行脚本

```bash
python3 forum/forum_extraction.py
```

运行大约 1-2 秒即完成（所有数据已内置，无需联网）。

你会看到类似这样的输出：

```
Total topics collected: 96
  U1 Toolchanger: 57
  U1 Troubleshooting guides: 20
  Update - U1 Toolchanger: 11
  U1 Featured Showcase Collection: 8

Topic classification:
  💬 讨论: 23
  🔴 问题/报错: 20
  📢 官方更新: 15
  🟡 疑问/求助: 15
  ...

✅ Report saved: forum/reports/forum_analysis_report.md

📁 Output files:
  forum/data/all_topics.json (88,300 bytes)
  forum/data/issue_list.json (31,102 bytes)
  ...
```

---

## 第五步：查看输出文件

运行后会生成 6 个文件：

| 文件 | 说明 | 怎么打开 |
|---|---|---|
| `forum/reports/forum_analysis_report.md` | 主报告（中文） | 任意文本编辑器 / VS Code / GitHub |
| `forum/data/all_topics.json` | 96 个帖子元数据 | 文本编辑器 / `python3 -m json.tool` |
| `forum/data/issue_list.json` | 35 个问题清单 | 同上 |
| `forum/data/feature_requests.json` | 8 个功能建议 | 同上 |
| `forum/data/unified_feedback_forum.json` | 统一格式数据 | 同上 |
| `forum/data/forum_data.xlsx` | Excel 汇总表 | Excel / WPS / Google Sheets |

快速查看报告：
```bash
# 方法1：直接在终端查看
cat forum/reports/forum_analysis_report.md

# 方法2：只看前 50 行摘要
head -50 forum/reports/forum_analysis_report.md

# 方法3：查看 JSON 数据（格式化输出）
python3 -m json.tool forum/data/feature_requests.json | head -30
```

---

## 脚本结构解读（给想理解代码的你）

`forum_extraction.py` 共 843 行，分 7 个阶段：

```
第1阶段 (22-144行)   → 数据定义：96个帖子的原始数据（硬编码）
第2阶段 (147-182行)  → 数据结构化：把元组变成字典列表
第3阶段 (279-427行)  → 帖子分类：用正则表达式自动识别帖子类型
第4阶段 (439-507行)  → 问题提取：筛选出问题帖，计算热度分数
第5阶段 (514-543行)  → 功能建议提取：筛选用户建议
第6阶段 (550-658行)  → 报告生成：输出 Markdown 格式的分析报告
第7阶段 (733-843行)  → 统一格式：输出跨平台标准化数据
```

关键函数：
- `classify_topic_type(title, category_id)` → 根据标题关键词分类帖子
- `classify_sentiment_forum(text)` → 情感分析（正面/负面/中性）
- `detect_language_simple(text)` → 语言检测（中/英/德）
- `compute_raw_engagement(item)` → 热度评分公式：`浏览量/50 + 回复×3 + 点赞×2`

---

## 常见问题

**Q: "ModuleNotFoundError: No module named 'pandas'"**
→ 运行 `pip install pandas openpyxl`

**Q: "Permission denied" 写文件时**
→ 确保 `forum/data/` 和 `forum/reports/` 目录存在：
```bash
mkdir -p forum/data forum/reports
```

**Q: 我想添加更多论坛帖子怎么办？**
→ 在脚本的 `RAW_TOPICS` 列表中添加新条目，格式：
```python
(topic_id, "slug", "Title", category_id, "2026-01-01", views, replies, likes, ["tag1"], False, False),
```
在 `TOPIC_SUMMARIES` 字典中添加对应摘要。

**Q: 如果网络代理问题解决了，怎么用 API 直接抓取？**
→ 原始任务描述中有完整的 Discourse API 抓取代码（使用 `requests` 库），
  可以替换硬编码数据为实时 API 调用。关键 API 端点：
  - 帖子列表: `https://forum.snapmaker.com/c/{category_id}.json?page={n}`
  - 帖子详情: `https://forum.snapmaker.com/t/{topic_id}.json`

---

## 一条命令总结

如果你在一台全新的机器上，从零运行只需要：

```bash
pip install pandas openpyxl && python3 forum/forum_extraction.py
```

输出结果在 `forum/reports/` 和 `forum/data/` 目录中。
