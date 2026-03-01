# Snapmaker U1 Facebook 用户反馈分析模块

对 Snapmaker U1 Official Facebook Group 的帖子进行多维度分析，输出含饼图、条形图和用户原声的 PPTX 报告。

## 分类体系设计（双维度）

### 维度一：内容类型（MECE — 互斥且完全穷尽）

每个帖子有且仅归入1个类别，总数 = 样本总数。

| 序号 | 分类 | 英文 | 定义与分类标准 |
|------|------|------|----------------|
| 1 | 问题/求助 | Questions / Help | 用户遇到了具体问题需要帮助，核心目的是**寻求解决方案** |
| 2 | 评价/反馈 | Reviews / Feedback | 用户对产品、服务或体验发表评价意见（无论正面还是负面） |
| 3 | 产品展示 | Product Showcase | 以展示3D打印成品**照片/视频**为主要内容（show & tell） |
| 4 | 其他 | Other | 无法归入以上类别的内容（纯转发、广告、不相关讨论等） |

### 维度二：情感倾向（独立于内容类型）

每个帖子有且仅归入1个情感标签。两个维度独立判断，任意组合合理。

| 标签 | 英文 | 定义 |
|------|------|------|
| 正面 | Positive | 帖子整体表达了满意、赞赏、推荐等正面情绪 |
| 负面 | Negative | 帖子整体表达了不满、失望、抱怨等负面情绪 |
| 中性 | Neutral | 无明显情感倾向，或正负混合难以判断 |

**典型组合示例**：
- "问题/求助 + 负面" = 带着不满情绪求助
- "问题/求助 + 中性" = 平静地提问
- "评价/反馈 + 正面" = 表达好评
- "产品展示 + 正面" = 兴奋地晒作品

### 子分类（第二层）

子分类按两个维度独立分组分析：

- **情感=正面** 的帖子 → 正面反馈子分类（多标签，每帖1-3个，总数可超过帖子数）
- **情感=负面** 的帖子 → 负面反馈子分类（多标签，每帖1-3个，总数可超过帖子数）
- **内容类型=问题/求助** 的帖子 → 问题子分类（MECE 单标签，总数 = 帖子数）

注意：一个帖子可能同时出现在多个子分类分析中（如"问题/求助+负面"的帖子会同时出现在问题子分类和负面子分类中）。

**正面反馈参考子类别**：

| 编号 | 子类别 | 英文 | 定义 |
|------|--------|------|------|
| P-01 | 打印质量好 | Print Quality | 打印精度高、表面光滑、细节清晰 |
| P-02 | 多色打印效果好 | Multi-color Printing | 多色/多材料效果惊艳 |
| P-03 | 换色效率高 | Efficient Color Change | 工具头切换快、耗材浪费少 |
| P-04 | 性价比高 | Good Value for Money | 物有所值 |
| P-05 | 设置简单/易用 | Easy Setup / User Friendly | 开箱简单、操作便捷 |
| P-06 | 客服/售后好 | Good Customer Service | 技术支持响应及时 |
| P-07 | 外观设计/做工好 | Good Build Quality | 外观美观、做工精细 |
| P-08 | 安静/噪音小 | Low Noise | 运行噪音低 |
| P-09 | 打印速度快 | Fast Printing Speed | 打印速度满意 |
| P-10 | 社区/生态好 | Great Community / Ecosystem | 社区活跃、互助氛围好 |
| P-11 | 其他正面 | Other Positive | 以上未覆盖的正面评价 |

**负面反馈参考子类别**：

| 编号 | 子类别 | 英文 | 定义 |
|------|--------|------|------|
| N-01 | 硬件质量/做工差 | Hardware Quality Issues | 静态质量缺陷（出厂即存在） |
| N-02 | 软件/固件问题 | Software / Firmware Issues | 切片软件BUG、固件问题 |
| N-03 | 打印质量不佳 | Poor Print Quality | 拉丝、层偏移、翘曲等 |
| N-04 | 售后服务差 | Poor Customer Service | 客服不回应、维修慢 |
| N-05 | 物流/发货问题 | Shipping / Delivery Issues | 发货慢、运输损坏 |
| N-06 | 噪音大 | Noisy | 运行噪音大、振动明显 |
| N-07 | 耗材兼容性差 | Material Compatibility | 第三方耗材不兼容 |
| N-08 | 稳定性差/频繁故障 | Poor Reliability | 频繁故障、需经常维修 |
| N-09 | 校准/设置困难 | Calibration Difficulty | 校准复杂、多次失败 |
| N-10 | 性价比低 | Poor Value | 功能与价格不匹配 |
| N-11 | 工具头/换头问题 | Toolhead Issues | 工具头拾取失败、碰撞 |
| N-12 | 其他负面 | Other Negative | 以上未覆盖的负面评价 |

**问题/求助参考子类别**：

| 编号 | 子类别 | 英文 | 定义 |
|------|--------|------|------|
| I-01 | 工具头问题 | Toolhead Issues | 拾取失败、校准偏移、碰撞 |
| I-02 | 打印质量问题 | Print Quality Issues | 拉丝、层偏移、首层附着力 |
| I-03 | 机械结构问题 | Mechanical Issues | 外壳、导轨、皮带、风扇 |
| I-04 | 电气/连接问题 | Electrical / Connection | WiFi、USB、电源、传感器 |
| I-05 | 软件/固件问题 | Software / Firmware | 切片软件BUG、固件问题 |
| I-06 | 耗材问题 | Material Issues | 兼容性、堵料、送料异常 |
| I-07 | 使用方法咨询 | Usage Questions | 设置方法、参数调整 |
| I-08 | 购买/配件咨询 | Purchase / Accessories | 购买建议、配件推荐 |
| I-09 | 售后支持 | After-sales Support | 客服响应、保修 |
| I-10 | 其他问题 | Other Issues | 以上未覆盖的问题 |

**LLM 自适应调整**：以上子类别为参考框架，LLM 可根据实际帖子内容灵活调整（合并/新建/重命名），保持子类别总数在合理范围内。

## 报告框架

```
PPTX 报告结构（共约 10 页）
│
├── 封面页
│
├── 第一章：数据概览 (Data Overview)
│     ├── 5 张统计卡片
│     ├── 帖子类型分布饼图
│     └── 高互动帖子 TOP10
│
├── 第二章：双维度分类总览
│     ├── 内容类型分布饼图（4 类）
│     ├── 情感倾向分布饼图（3 类）
│     └── 交叉分布统计
│
├── 第三章：正面反馈分析 ── 2 页（情感=正面）
│     ├── 页1：子分类条形图 + 饼图
│     └── 页2：用户原声
│
├── 第四章：负面反馈分析 ── 2 页（情感=负面）
│     ├── 页1：子分类条形图 + 饼图
│     └── 页2：用户原声
│
├── 第五章：问题/求助分析 ── 2 页（内容类型=问题/求助）
│     ├── 页1：子分类条形图 + 饼图
│     └── 页2：用户原声
│
├── 第六章：竞品提及分析
│
└── 附录：分析方法说明
```

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

### 3. 运行分析

```bash
# 默认使用 Qwen LLM 分类（需配置 .env）
python analyze.py facebook_data.json

# 指定输出目录
python analyze.py facebook_data.json --output ./reports/

# 禁用 LLM，仅用关键词规则分类
python analyze.py facebook_data.json --no-llm
```

## 报告规范

- **输出语言**：简体中文，英文原文以括号标注
- **中文字体**：等线 (DengXian)
- **英文字体**：Calibri
- **图表**：饼图和条形图，使用 matplotlib 生成
- **用户原声**：保留英文原文，每个子类别展示 1-3 条代表性帖子
