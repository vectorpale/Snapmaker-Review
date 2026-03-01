# Snapmaker U1 Facebook 用户反馈分析模块

对 Snapmaker U1 Official Facebook Group 的帖子进行多维度分析，输出含饼图、条形图和用户原声的 PPTX 报告。

## 报告框架

```
PPTX 报告结构（共约 11 页）
│
├── 封面页
│     Snapmaker U1 Facebook 用户反馈分析报告
│     数据来源、帖子总数、评论总数、采集时间
│
├── 第一章：数据概览 (Data Overview)
│     ├── 5 张统计卡片：帖子总数、评论总数、独立作者数、平均反应数、平均评论数
│     ├── 帖子类型分布饼图：纯文本 / 含图片 / 含视频
│     └── 高互动帖子 TOP10 列表
│
├── 第二章：主贴分类总览 (Post Classification) ── MECE 五分类
│     ├── 分类分布饼图（总数 = 样本数，严格互斥）
│     │     1. 问题/求助 (Questions / Help)
│     │     2. 打印结果展示/晒作品 (Print Showcase)
│     │     3. 正面评价 (Positive Reviews)
│     │     4. 负面评价 (Negative Reviews)
│     │     5. 无意义 (Irrelevant)
│     ├── 各类别统计数字和占比
│     └── 分析方法说明（关键词 / LLM）
│
├── 第三章：正面评价分析 (Positive Reviews Analysis) ── 2 页
│     ├── 页1：子分类条形图 + 饼图（MECE，每帖归入1个子类别）
│     │     子类别示例：打印质量好、多色打印效果好、性价比高、设置简单/易用...
│     └── 页2：用户原声 (User Voices)
│           每个子类别展示 1-2 条代表性英文原文
│
├── 第四章：负面评价分析 (Negative Reviews Analysis) ── 2 页
│     ├── 页1：子分类条形图 + 饼图（MECE）
│     │     子类别示例：硬件质量问题、软件/固件问题、售后服务差、可靠性/故障率高...
│     └── 页2：用户原声 (User Voices)
│
├── 第五章：问题/求助分析 (Issues Analysis) ── 2 页
│     ├── 页1：子分类条形图 + 饼图（MECE）
│     │     子类别示例：工具头问题、打印质量问题、机械结构问题、电气/连接问题...
│     └── 页2：用户原声 (User Voices)
│
├── 第六章：竞品提及分析 (Competitor Mentions)
│     ├── 竞品品牌提及次数条形图
│     └── 统计说明
│
├── 第七章：情感分析总览 (Sentiment Overview)
│     ├── 情感分布饼图：正面 / 负面 / 中性 / 混合
│     └── 分类与情感交叉分析
│
└── 附录：分析方法说明 (Methodology)
      分类方法、字体规范、数据处理说明
```

## 分类体系设计（MECE 原则）

### 第一层：主贴五分类（互斥且完全穷尽）

每个帖子有且仅归入1个类别，总数 = 样本总数。

| 序号 | 分类 | 英文 | 说明 |
|------|------|------|------|
| 1 | 问题/求助 | Questions / Help | 遇到问题、报告故障、寻求技术支持 |
| 2 | 打印结果展示/晒作品 | Print Showcase | 展示3D打印成品、分享作品照片 |
| 3 | 正面评价 | Positive Reviews | 对产品/服务表达正面评价和赞赏 |
| 4 | 负面评价 | Negative Reviews | 对产品/服务表达不满和批评 |
| 5 | 无意义 | Irrelevant | 不相关内容、纯转发、广告等 |

### 第二层：子分类（各大类内部 MECE）

每个帖子在其所属大类内仅归入1个子类别。

**正面评价子类别：**

| 子类别 | 英文 | 说明 |
|--------|------|------|
| 打印质量好 | Print Quality | 打印精度高、表面光滑 |
| 多色打印效果好 | Multi-color Printing | 多色/多材料效果惊艳 |
| 换头速度快/浪费少 | Fast Tool Change | 工具头切换快、耗材浪费少 |
| 性价比高 | Good Value | 物有所值 |
| 设置简单/易用 | Easy Setup | 安装简单、操作友好 |
| 客服/售后好 | Good Service | 技术支持好 |
| 外观设计/做工好 | Good Build Quality | 外观、做工、用料好 |
| 安静/噪音小 | Low Noise | 运行安静 |
| 打印速度快 | Fast Printing | 速度满意 |
| 社区互助好 | Great Community | 社区帮助好 |
| 其他正面 | Other Positive | 以上未覆盖 |

**负面评价子类别：**

| 子类别 | 英文 | 说明 |
|--------|------|------|
| 硬件质量/做工差 | Hardware Quality | 机械部件质量问题 |
| 软件/固件问题 | Software/Firmware | 切片软件、固件BUG |
| 打印质量不佳 | Poor Print Quality | 拉丝、层偏移等缺陷 |
| 售后服务差 | Poor Service | 客服不回应、维修慢 |
| 物流/发货问题 | Shipping Issues | 发货慢、包装损坏 |
| 噪音大 | Noisy | 运行噪音大 |
| 耗材兼容性差 | Material Compatibility | 第三方耗材不兼容 |
| 可靠性/故障率高 | High Failure Rate | 频繁故障 |
| 校准/设置困难 | Calibration Difficulty | 校准复杂 |
| 性价比低 | Poor Value | 不值价格 |
| 其他负面 | Other Negative | 以上未覆盖 |

**问题/求助子类别：**

| 子类别 | 英文 | 说明 |
|--------|------|------|
| 工具头问题 | Toolhead Issues | 拾取失败、校准偏移、碰撞 |
| 打印质量问题 | Print Quality Issues | 拉丝、层偏移、首层附着力 |
| 机械结构问题 | Mechanical Issues | 外壳、导轨、皮带、风扇 |
| 电气/连接问题 | Electrical/Connection | WiFi、USB、电源、传感器 |
| 软件/固件问题 | Software/Firmware | 切片软件BUG、固件问题 |
| 耗材问题 | Material Issues | 兼容性、堵料、送料异常 |
| 使用咨询 | Usage Questions | 设置方法、参数调整 |
| 购买/配件咨询 | Purchase/Accessories | 购买建议、配件推荐 |
| 售后支持问题 | After-sales Support | 客服响应、保修 |
| 其他问题 | Other Issues | 以上未覆盖 |

## 快速开始

### 1. 安装依赖

```bash
cd facebook/
pip install -r requirements.txt
```

### 2. 配置 LLM（可选）

复制 `.env.example` 为 `.env` 并填入 Qwen API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

`.env` 文件内容：
```
QWEN_API_KEY=your_api_key_here
QWEN_MODEL=qwen-plus
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 3. 运行分析

```bash
# 仅关键词分类（无需 API Key）
python analyze.py facebook_data.json

# 使用 Qwen LLM 增强分类（推荐）
python analyze.py facebook_data.json --llm

# 指定输出目录
python analyze.py facebook_data.json --llm --output ./reports/
```

## 输入数据格式

JSON 文件，结构如下：

```json
{
  "group_url": "https://www.facebook.com/groups/snapmakeru1/",
  "group_name": "Snapmaker U1 Official Group",
  "total_posts": 810,
  "total_comments": 2000,
  "posts": [
    {
      "post_id": "...",
      "author": "User Name",
      "text": "Post content...",
      "reactions": 15,
      "comment_count": 5,
      "has_image": true,
      "has_video": false,
      "comments": [
        {"text": "Comment text...", "author": "..."}
      ]
    }
  ]
}
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `output/analysis_result.json` | 每个帖子的分类和情感分析结果 |
| `output/report.pptx` | 完整 PPTX 分析报告 |

## 报告规范

- **输出语言**：简体中文，英文原文以括号标注
- **中文字体**：等线 (DengXian)
- **英文字体**：Calibri
- **图表**：饼图和条形图，使用 matplotlib 生成
- **用户原声**：保留英文原文，每个子类别展示 1-3 条代表性帖子

## 项目结构

```
facebook/
├── analyze.py              # 主入口：分析流程编排
├── classifier.py           # 细粒度关键词分类引擎
├── sentiment.py            # 情感分析引擎
├── llm_client.py           # Qwen LLM API 客户端
├── report_generator.py     # PPTX 报告生成器
├── keywords/               # 关键词词典 (JSON)
│   ├── hardware.json
│   ├── software.json
│   ├── material.json
│   ├── ux.json
│   ├── positive.json
│   └── sentiment.json
├── requirements.txt
├── .env.example            # API 配置模板
├── .gitignore
└── output/                 # 生成的报告
```

## 技术架构

```
输入 JSON ──→ 细粒度分类 (classifier.py)  ──→ 情感分析 (sentiment.py)
                                                    │
                                                    ▼
                                           主贴五分类 (MECE)
                                           ┌─ 关键词规则 (默认)
                                           └─ Qwen LLM (--llm)
                                                    │
                                                    ▼
                                           子分类深度分析 (MECE)
                                           ┌─ 关键词回退 (默认)
                                           └─ Qwen LLM (--llm)
                                                    │
                                                    ▼
                                           统计汇总 + 报告生成
                                                    │
                                                    ▼
                                    analysis_result.json + report.pptx
```
