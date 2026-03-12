"""
LLM client for Qwen API integration.

Uses the OpenAI-compatible DashScope endpoint to call Qwen models
for post classification and sub-category analysis.

分类体系：双维度
  维度一 — 内容类型 (MECE): 问题/求助、评价/反馈、产品展示、其他
  维度二 — 情感倾向: 正面、负面、中性
"""

import json
import os
import re
import time
from typing import Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ── Prompt templates ─────────────────────────────────────────────

PRIMARY_CLASSIFY_PROMPT = """你是一个专业的用户反馈分析师。请对以下来自 Snapmaker U1 3D打印机 Facebook 用户群的帖子进行**双维度分类**。

【维度一：内容类型】（MECE — 互斥且完全穷尽，每帖仅归入1个）
1. 问题/求助 — 用户遇到了具体问题需要帮助，核心目的是寻求解决方案（如报告故障、提问技术问题、请求指导）
2. 评价/反馈 — 用户对产品、服务或体验发表评价意见（无论正面还是负面，核心目的是表达观点）
3. 产品展示 — 以展示3D打印成品照片/视频为主要内容（show & tell、晒作品）
4. 其他 — 无法归入以上类别的内容（纯转发、广告、不相关讨论、通知等）

【维度二：情感倾向】（独立于内容类型，每帖仅归入1个）
1. 正面 — 帖子整体表达了满意、赞赏、推荐等正面情绪
2. 负面 — 帖子整体表达了不满、失望、抱怨等负面情绪
3. 中性 — 无明显情感倾向，或正负混合难以判断

【重要说明】
- 两个维度独立判断，任意组合都是合理的。例如：
  - "问题/求助 + 负面" = 带着不满情绪求助
  - "问题/求助 + 中性" = 平静地提问
  - "评价/反馈 + 正面" = 表达好评
  - "产品展示 + 正面" = 兴奋地晒作品

请以JSON格式返回结果：
{
  "content_type": "问题/求助" 或 "评价/反馈" 或 "产品展示" 或 "其他",
  "sentiment": "正面" 或 "负面" 或 "中性",
  "confidence": 0.0-1.0,
  "brief_reason": "简短分类理由"
}

帖子内容：
"""

POSITIVE_SUBCATEGORY_PROMPT = """你是一个专业的用户反馈分析师。以下是来自 Snapmaker U1 3D打印机用户群的**情感倾向为正面**的帖子。

【重要】一个帖子可能涉及多个正面维度，请选出1-3个最相关的子类别（允许多选）。

以下子类别为参考框架（编号 + 名称 + 定义）：
P-01 打印质量好 (Print Quality) — 打印精度高、表面光滑、细节清晰、尺寸准确
P-02 多色打印效果好 (Multi-color Printing) — 多色/多材料打印的颜色过渡自然、对齐精准、整体效果惊艳
P-03 换色效率高 (Efficient Color Change) — 工具头切换速度快、换色过程耗材浪费少
P-04 性价比高 (Good Value for Money) — 相对价格功能丰富、物有所值
P-05 设置简单/易用 (Easy Setup / User Friendly) — 开箱组装简单、日常操作便捷、学习成本低
P-06 客服/售后好 (Good Customer Service) — 技术支持响应及时、售后问题处理令人满意
P-07 外观设计/做工好 (Good Build Quality) — 机器外观美观、结构用料扎实、做工精细
P-08 安静/噪音小 (Low Noise) — 运行噪音低、不影响正常生活/工作环境
P-09 打印速度快 (Fast Printing Speed) — 打印速度令人满意、效率高
P-10 社区/生态好 (Great Community / Ecosystem) — 用户社区活跃、资源丰富、互助氛围好
P-11 其他正面 (Other Positive) — 以上类别无法覆盖的正面评价

【自适应调整】以上子类别为参考框架。你可以根据实际帖子内容灵活调整：
- 如果大量帖子涉及参考框架未覆盖的正面维度，可以创建新的描述性类别
- 如果某些类别边界模糊难以区分，可以合并
- 保持子类别总数在8-15个范围内

对每个帖子，返回JSON格式：
{
  "subcategories": ["P-01 打印质量好", "P-02 多色打印效果好"],
  "representative_quote": "最能代表该正面评价的原始文字片段（英文原文）",
  "summary": "一句话中文总结"
}

注意：subcategories 为数组，选1-3个最相关的子类别。可使用参考编号+名称，也可自定义新类别名称。

帖子列表（JSON数组）：
"""

NEGATIVE_SUBCATEGORY_PROMPT = """你是一个专业的用户反馈分析师。以下是来自 Snapmaker U1 3D打印机用户群的**情感倾向为负面**的帖子。

【重要】一个帖子可能涉及多个负面维度，请选出1-3个最相关的子类别（允许多选）。

以下子类别为参考框架（编号 + 名称 + 定义）：
N-01 硬件质量/做工差 (Hardware Quality Issues) — 机械部件、外壳、导轨等静态质量缺陷（收到时即存在的问题）
N-02 软件/固件问题 (Software / Firmware Issues) — 切片软件BUG、固件更新失败、APP崩溃等软件层面问题
N-03 打印质量不佳 (Poor Print Quality) — 拉丝、层偏移、表面粗糙、翘曲等打印成品缺陷
N-04 售后服务差 (Poor Customer Service) — 客服不回应、维修周期长、处理态度差
N-05 物流/发货问题 (Shipping / Delivery Issues) — 发货慢、运输途中损坏、配件缺失
N-06 噪音大 (Noisy) — 运行噪音大、振动明显、影响使用环境
N-07 耗材兼容性差 (Material Compatibility) — 第三方耗材不兼容、频繁堵料
N-08 稳定性差/频繁故障 (Poor Reliability / Frequent Failures) — 使用过程中频繁出现故障、需要经常维修（区别于N-01：N-01是出厂缺陷，N-08是使用中的可靠性问题）
N-09 校准/设置困难 (Calibration Difficulty) — 校准流程复杂、多次失败、初始设置繁琐
N-10 性价比低 (Poor Value) — 功能与价格不匹配、觉得不值
N-11 工具头/换头问题 (Toolhead / Tool Change Issues) — 工具头拾取失败、换头过程故障、碰撞等
N-12 其他负面 (Other Negative) — 以上类别无法覆盖的负面评价

【自适应调整】以上子类别为参考框架。你可以根据实际帖子内容灵活调整：
- 如果大量帖子涉及参考框架未覆盖的负面维度，可以创建新的描述性类别
- 如果某些类别边界模糊难以区分，可以合并
- 保持子类别总数在8-15个范围内

对每个帖子，返回JSON格式：
{
  "subcategories": ["N-01 硬件质量/做工差", "N-08 稳定性差/频繁故障"],
  "representative_quote": "最能代表该负面评价的原始文字片段（英文原文）",
  "summary": "一句话中文总结"
}

注意：subcategories 为数组，选1-3个最相关的子类别。可使用参考编号+名称，也可自定义新类别名称。

帖子列表（JSON数组）：
"""

ISSUE_SUBCATEGORY_PROMPT = """你是一个专业的用户反馈分析师。以下是来自 Snapmaker U1 3D打印机用户群的**内容类型为问题/求助**的帖子。

【重要】子分类必须遵循 MECE 原则：每个帖子只归入1个最主要的子类别。

以下子类别为参考框架（编号 + 名称 + 定义，MECE，选其一）：
I-01 工具头问题 (Toolhead Issues) — 工具头拾取/停放失败、校准偏移、碰撞、加热异常
I-02 打印质量问题 (Print Quality Issues) — 拉丝、层偏移、首层附着力差、翘曲、表面缺陷
I-03 机械结构问题 (Mechanical Issues) — 外壳松脱、导轨磨损、皮带异响、风扇故障
I-04 电气/连接问题 (Electrical / Connection) — WiFi断连、USB通信故障、电源异常、传感器失灵
I-05 软件/固件问题 (Software / Firmware) — 切片软件BUG、固件更新失败、APP异常
I-06 耗材问题 (Material Issues) — 耗材兼容性、堵料、送料异常、耗材受潮
I-07 使用方法咨询 (Usage Questions) — 设置方法、打印参数调整、功能使用咨询
I-08 购买/配件咨询 (Purchase / Accessories) — 购买建议、配件推荐、兼容性咨询
I-09 售后支持 (After-sales Support) — 客服响应、保修政策、退换货流程
I-10 其他问题 (Other Issues) — 以上类别无法覆盖的问题

【自适应调整】以上子类别为参考框架。你可以根据实际帖子内容灵活调整：
- 如果大量帖子涉及参考框架未覆盖的问题类型，可以创建新的描述性类别
- 如果某些类别边界模糊难以区分，可以合并
- 保持子类别总数在8-12个范围内

对每个帖子，返回JSON格式：
{
  "subcategory": "I-01 工具头问题",
  "representative_quote": "最能代表该问题的原始文字片段（英文原文）",
  "summary": "一句话中文总结"
}

注意：subcategory 为单一字符串。可使用参考编号+名称，也可自定义新类别名称。

帖子列表（JSON数组）：
"""


class LLMClient:
    """Client for calling Qwen LLM via OpenAI-compatible API."""

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        if OpenAI is None:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        self.api_key = api_key or os.environ.get("QWEN_API_KEY", "")
        self.model = model or os.environ.get("QWEN_MODEL", "qwen-plus")
        self.base_url = base_url or os.environ.get(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        if not self.api_key:
            raise ValueError(
                "API key is required. Set QWEN_API_KEY in .env or pass api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call LLM with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的用户反馈分析师，专注于3D打印机产品。请始终以纯JSON格式回复，不要添加任何额外文字、解释或markdown格式。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"  LLM call failed (attempt {attempt + 1}): {e}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  LLM call failed after {max_retries} attempts: {e}")
                    raise

    def _parse_json_response(self, text: str) -> any:
        """Parse JSON from LLM response, handling thinking tags, markdown code blocks, etc."""
        text = text.strip()

        # Strip Qwen 3.5 thinking mode tags: <think>...</think>
        text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

        # Try direct parse first (fast path)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Extract from markdown code blocks (```json ... ``` or ``` ... ```)
        md_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)```", text)
        if md_match:
            try:
                return json.loads(md_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Last resort: find the outermost JSON array or object in the text
        # Try array first (batch responses are arrays), then object
        for open_char, close_char in [("[", "]"), ("{", "}")]:
            start = text.find(open_char)
            if start == -1:
                continue
            # Find matching closing bracket by scanning from the end
            end = text.rfind(close_char)
            if end > start:
                candidate = text[start:end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

        # All strategies failed – raise with context for debugging
        preview = text[:200] + ("..." if len(text) > 200 else "")
        raise json.JSONDecodeError(
            f"No valid JSON found in LLM response. Preview: {preview}",
            text, 0
        )

    def classify_post(self, post_text: str) -> Dict:
        """Classify a single post: content_type + sentiment."""
        prompt = PRIMARY_CLASSIFY_PROMPT + post_text[:2000]
        try:
            result_text = self._call_llm(prompt)
            result = self._parse_json_response(result_text)
            return result
        except (json.JSONDecodeError, Exception) as e:
            print(f"  Warning: Failed to parse LLM classification result: {e}")
            return {
                "content_type": "其他",
                "sentiment": "中性",
                "confidence": 0.1,
                "brief_reason": "LLM解析失败"
            }

    def classify_posts_batch(self, posts: List[Dict], batch_size: int = 10) -> List[Dict]:
        """Classify posts in batches for efficiency."""
        results = []
        total = len(posts)

        for i in range(0, total, batch_size):
            batch = posts[i:i + batch_size]
            batch_texts = []
            for j, post in enumerate(batch):
                text = (post.get("text", "") or "")[:500]
                batch_texts.append({"id": i + j, "text": text})

            prompt = PRIMARY_CLASSIFY_PROMPT + "\n请对以下多个帖子逐一分类，返回JSON数组：\n" + json.dumps(batch_texts, ensure_ascii=False)

            try:
                result_text = self._call_llm(prompt)
                batch_results = self._parse_json_response(result_text)
                if isinstance(batch_results, list):
                    results.extend(batch_results)
                elif isinstance(batch_results, dict):
                    results.append(batch_results)
            except Exception as e:
                print(f"  Batch {i // batch_size + 1} failed: {e}, classifying individually...")
                for post in batch:
                    result = self.classify_post(post.get("text", ""))
                    results.append(result)

            if (i + batch_size) < total:
                print(f"  已分类 {min(i + batch_size, total)}/{total} 个帖子...")
                time.sleep(0.5)

        return results

    def analyze_subcategories(self, posts: List[Dict], category_type: str) -> List[Dict]:
        """
        Analyze subcategories for a group of posts.

        Args:
            posts: List of post dicts with at least 'text' field
            category_type: One of 'positive', 'negative', 'issue'
        """
        prompt_map = {
            "positive": POSITIVE_SUBCATEGORY_PROMPT,
            "negative": NEGATIVE_SUBCATEGORY_PROMPT,
            "issue": ISSUE_SUBCATEGORY_PROMPT,
        }
        base_prompt = prompt_map.get(category_type, ISSUE_SUBCATEGORY_PROMPT)

        results = []
        batch_size = 5
        total = len(posts)

        for i in range(0, total, batch_size):
            batch = posts[i:i + batch_size]
            batch_data = []
            for j, post in enumerate(batch):
                text = (post.get("text", "") or "")[:800]
                author = post.get("author", "Anonymous")
                batch_data.append({"id": i + j, "author": author, "text": text})

            prompt = base_prompt + json.dumps(batch_data, ensure_ascii=False)

            try:
                result_text = self._call_llm(prompt)
                batch_results = self._parse_json_response(result_text)
                if isinstance(batch_results, list):
                    results.extend(batch_results)
                elif isinstance(batch_results, dict):
                    results.append(batch_results)
            except Exception as e:
                print(f"  Sub-category batch {i // batch_size + 1} failed: {e}")
                for post in batch:
                    results.append({
                        "subcategories": ["未分类"],
                        "representative_quote": (post.get("text", "") or "")[:100],
                        "summary": "分析失败",
                    })

            if (i + batch_size) < total:
                time.sleep(0.5)

        return results
