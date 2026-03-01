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
│     │     3. 正面反馈 (Positive Feedback)
│     │     4. 负面反馈 (Negative Feedback)
│     │     5. 其他内容 (Other Content)
│     ├── 各类别统计数字和占比
│     └── 分析方法说明（关键词 / LLM）
│
├── 第三章：正面反馈分析 (Positive Feedback Analysis) ── 2 页
│     ├── 页1：子分类条形图 + 饼图（多标签，总数可超过帖子数）
│     │     子类别：P-01 打印质量好、P-02 多色打印效果好、P-03 换色效率高...
│     └── 页2：用户原声 (User Voices)
│           每个子类别展示 1-2 条代表性英文原文
│
├── 第四章：负面反馈分析 (Negative Feedback Analysis) ── 2 页
│     ├── 页1：子分类条形图 + 饼图（多标签，总数可超过帖子数）
│     │     子类别：N-01 硬件质量/做工差、N-02 软件/固件问题、N-06 噪音大...
│     └── 页2：用户原声 (User Voices)
│
├── 第五章：问题/求助分析 (Issues Analysis) ── 2 页
│     ├── 页1：子分类条形图 + 饼图（MECE 单标签，总数 = 帖子数）
│     │     子类别：I-01 工具头问题、I-02 打印质量问题、I-03 机械结构问题...
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

## 分类体系设计

### 第一层：主贴五分类（MECE — 互斥且完全穷尽）

每个帖子有且仅归入1个类别，总数 = 样本总数。

| 序号 | 分类 | 英文 | 定义与分类标准 |
|------|------|------|----------------|
| 1 | 问题/求助 | Questions / Help | 用户遇到了具体问题需要帮助，核心目的是**寻求解决方案**（如报告故障、提问技术问题）。判定关键：帖子意图是"求解决"而非"发泄不满" |
| 2 | 打印结果展示/晒作品 | Print Showcase | 以展示3D打印成品**照片/视频**为主要内容（show & tell）。判定关键：内容载体是**图片展示**而非纯文字评价 |
| 3 | 正面反馈 | Positive Feedback | 对产品、服务或体验表达正面评价和赞赏（不含纯作品展示）。判定关键：以**文字评价**为主，表达满意/推荐 |
| 4 | 负面反馈 | Negative Feedback | 对产品、服务或体验表达不满、抱怨或批评。判定关键：重点是**情绪表达**（抱怨/失望），而非寻求技术帮助 |
| 5 | 其他内容 | Other Content | 无法归入以上类别的内容，如纯转发、广告、不相关讨论等 |

**边缘情况优先级阶梯**：问题/求助 > 打印结果展示 > 负面反馈 > 正面反馈 > 其他内容

### 第二层：正面反馈子类别（多标签，1-3个/帖）

一个帖子可能涉及多个正面维度，允许选出1-3个最相关的子类别，因此子类别总数可超过帖子数。

| 编号 | 子类别 | 英文 | 定义与分类标准 |
|------|--------|------|----------------|
| P-01 | 打印质量好 | Print Quality | 打印精度高、表面光滑、细节清晰、尺寸准确 |
| P-02 | 多色打印效果好 | Multi-color Printing | 多色/多材料打印的颜色过渡自然、对齐精准、整体效果惊艳 |
| P-03 | 换色效率高 | Efficient Color Change | 工具头切换速度快、换色过程耗材浪费少 |
| P-04 | 性价比高 | Good Value for Money | 相对价格功能丰富、物有所值 |
| P-05 | 设置简单/易用 | Easy Setup / User Friendly | 开箱组装简单、日常操作便捷、学习成本低 |
| P-06 | 客服/售后好 | Good Customer Service | 技术支持响应及时、售后问题处理令人满意 |
| P-07 | 外观设计/做工好 | Good Build Quality | 机器外观美观、结构用料扎实、做工精细 |
| P-08 | 安静/噪音小 | Low Noise | 运行噪音低、不影响正常生活/工作环境 |
| P-09 | 打印速度快 | Fast Printing Speed | 打印速度令人满意、效率高 |
| P-10 | 社区/生态好 | Great Community / Ecosystem | 用户社区活跃、资源丰富、互助氛围好 |
| P-11 | 其他正面 | Other Positive | 以上类别无法覆盖的正面评价 |

### 第二层：负面反馈子类别（多标签，1-3个/帖）

一个帖子可能涉及多个负面维度，允许选出1-3个最相关的子类别，因此子类别总数可超过帖子数。

| 编号 | 子类别 | 英文 | 定义与分类标准 |
|------|--------|------|----------------|
| N-01 | 硬件质量/做工差 | Hardware Quality Issues | 机械部件、外壳、导轨等**静态质量缺陷**（收到时即存在的问题） |
| N-02 | 软件/固件问题 | Software / Firmware Issues | 切片软件BUG、固件更新失败、APP崩溃等软件层面问题 |
| N-03 | 打印质量不佳 | Poor Print Quality | 拉丝、层偏移、表面粗糙、翘曲等打印成品缺陷 |
| N-04 | 售后服务差 | Poor Customer Service | 客服不回应、维修周期长、处理态度差 |
| N-05 | 物流/发货问题 | Shipping / Delivery Issues | 发货慢、运输途中损坏、配件缺失 |
| N-06 | 噪音大 | Noisy | 运行噪音大、振动明显、影响使用环境 |
| N-07 | 耗材兼容性差 | Material Compatibility | 第三方耗材不兼容、频繁堵料 |
| N-08 | 稳定性差/频繁故障 | Poor Reliability / Frequent Failures | 使用过程中频繁出现故障、需要经常维修（区别于N-01：N-01是出厂缺陷，N-08是使用中的可靠性问题） |
| N-09 | 校准/设置困难 | Calibration Difficulty | 校准流程复杂、多次失败、初始设置繁琐 |
| N-10 | 性价比低 | Poor Value | 功能与价格不匹配、觉得不值 |
| N-11 | 工具头/换头问题 | Toolhead / Tool Change Issues | 工具头拾取失败、换头过程故障、碰撞等 |
| N-12 | 其他负面 | Other Negative | 以上类别无法覆盖的负面评价 |

### 第二层：问题/求助子类别（MECE 单标签，1个/帖）

每个帖子在其所属大类内仅归入1个子类别，总数 = 帖子数。

| 编号 | 子类别 | 英文 | 定义与分类标准 |
|------|--------|------|----------------|
| I-01 | 工具头问题 | Toolhead Issues | 工具头拾取/停放失败、校准偏移、碰撞、加热异常 |
| I-02 | 打印质量问题 | Print Quality Issues | 拉丝、层偏移、首层附着力差、翘曲、表面缺陷 |
| I-03 | 机械结构问题 | Mechanical Issues | 外壳松脱、导轨磨损、皮带异响、风扇故障 |
| I-04 | 电气/连接问题 | Electrical / Connection | WiFi断连、USB通信故障、电源异常、传感器失灵 |
| I-05 | 软件/固件问题 | Software / Firmware | 切片软件BUG、固件更新失败、APP异常 |
| I-06 | 耗材问题 | Material Issues | 耗材兼容性、堵料、送料异常、耗材受潮 |
| I-07 | 使用方法咨询 | Usage Questions | 设置方法、打印参数调整、功能使用咨询 |
| I-08 | 购买/配件咨询 | Purchase / Accessories | 购买建议、配件推荐、兼容性咨询 |
| I-09 | 售后支持 | After-sales Support | 客服响应、保修政策、退换货流程 |
| I-10 | 其他问题 | Other Issues | 以上类别无法覆盖的问题 |

## 快速开始

### 1. 安装依赖

```bash
cd facebook/
pip install -r requirements.txt
```

### 2. 配置 LLM

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
# 默认使用 Qwen LLM 分类（需配置 .env）
python analyze.py facebook_data.json

# 指定输出目录
python analyze.py facebook_data.json --output ./reports/

# 禁用 LLM，仅用关键词规则分类
python analyze.py facebook_data.json --no-llm
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
                                           子分类深度分析
                                           ┌─ 正面/负面: 多标签 (1-3个)
                                           └─ 问题/求助: MECE 单标签
                                           ┌─ 关键词回退 (默认)
                                           └─ Qwen LLM (--llm)
                                                    │
                                                    ▼
                                           统计汇总 + 报告生成
                                                    │
                                                    ▼
                                    analysis_result.json + report.pptx
```
