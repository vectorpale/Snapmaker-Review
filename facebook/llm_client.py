"""
LLM client for Qwen API integration.

Uses the OpenAI-compatible DashScope endpoint to call Qwen models
for post classification and sub-category analysis.
"""

import json
import os
import time
from typing import Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ── Prompt templates ─────────────────────────────────────────────

PRIMARY_CLASSIFY_PROMPT = """你是一个专业的用户反馈分析师。请对以下来自 Snapmaker U1 3D打印机 Facebook 用户群的帖子进行分类。

【重要】分类必须遵循 MECE 原则（互斥且完全穷尽）：每个帖子有且仅归入以下5个类别中的1个：
1. 问题/求助 - 用户遇到了问题需要帮助、报告了故障或BUG、寻求技术支持
2. 打印结果展示/晒作品 - 用户展示自己的3D打印成品、分享作品照片、show & tell
3. 正面评价 - 用户对产品、服务或体验表达正面评价和赞赏（不含展示作品）
4. 负面评价 - 用户对产品、服务或体验表达不满、抱怨或批评（区别于"问题/求助"：这里的重点是抱怨情绪而非寻求帮助）
5. 无意义 - 无法归入以上类别，或内容不相关、纯转发、广告等

判断优先级提示：
- 如果帖子主要目的是展示打印成品/照片 → "打印结果展示/晒作品"
- 如果帖子在求助/提问/报错 → "问题/求助"
- 如果帖子主要是表达不满/抱怨 → "负面评价"
- 如果帖子主要是表达满意/称赞 → "正面评价"

请以JSON格式返回结果，格式为：
{
  "category": "问题/求助" 或 "打印结果展示/晒作品" 或 "正面评价" 或 "负面评价" 或 "无意义",
  "confidence": 0.0-1.0,
  "brief_reason": "简短分类理由"
}

帖子内容：
"""

POSITIVE_SUBCATEGORY_PROMPT = """你是一个专业的用户反馈分析师。以下是来自 Snapmaker U1 3D打印机用户群的正面评价帖子。

【重要】子分类必须遵循 MECE 原则：每个帖子只归入1个最主要的子类别。

正面评价子类别（MECE，选其一）：
1. 打印质量好 (Print Quality) - 打印精度高、表面光滑、细节清晰
2. 多色打印效果好 (Multi-color Printing) - 多色/多材料打印效果惊艳
3. 换头速度快/浪费少 (Fast Tool Change / Less Waste) - 工具头切换快、耗材浪费少
4. 性价比高 (Good Value for Money) - 物有所值、价格合理
5. 设置简单/易用 (Easy Setup / User Friendly) - 安装简单、操作友好、开箱即用
6. 客服/售后好 (Good Customer Service) - 技术支持响应快、售后服务好
7. 外观设计/做工好 (Good Build Quality) - 机器外观、做工、用料好
8. 安静/噪音小 (Low Noise) - 运行安静
9. 打印速度快 (Fast Printing Speed) - 打印速度令人满意
10. 社区互助好 (Great Community) - 感谢社区帮助、分享知识
11. 其他正面 (Other Positive) - 以上类别无法覆盖的正面评价

对每个帖子，返回JSON格式：
{
  "subcategory": "选择1个最主要的子类别名称",
  "representative_quote": "最能代表该正面评价的原始文字片段（英文原文）",
  "summary": "一句话中文总结"
}

帖子列表（JSON数组）：
"""

NEGATIVE_SUBCATEGORY_PROMPT = """你是一个专业的用户反馈分析师。以下是来自 Snapmaker U1 3D打印机用户群的负面评价帖子。

【重要】子分类必须遵循 MECE 原则：每个帖子只归入1个最主要的子类别。

负面评价子类别（MECE，选其一）：
1. 硬件质量/做工差 (Hardware Quality Issues) - 机械部件、外壳、导轨等质量问题
2. 软件/固件问题 (Software / Firmware Issues) - 切片软件、固件BUG、APP崩溃等
3. 打印质量不佳 (Poor Print Quality) - 拉丝、层偏移、表面粗糙等打印缺陷
4. 售后服务差 (Poor Customer Service) - 客服不回应、维修慢、态度差
5. 物流/发货问题 (Shipping / Delivery Issues) - 发货慢、包装损坏、配件缺失
6. 噪音大 (Noisy) - 运行噪音大、振动严重
7. 耗材兼容性差 (Material Compatibility) - 第三方耗材不兼容、堵料
8. 可靠性/故障率高 (Reliability / High Failure Rate) - 频繁故障、需要经常维修
9. 校准/设置困难 (Calibration Difficulty) - 校准复杂、多次失败
10. 性价比低 (Poor Value) - 觉得不值这个价格
11. 其他负面 (Other Negative) - 以上类别无法覆盖的负面评价

对每个帖子，返回JSON格式：
{
  "subcategory": "选择1个最主要的子类别名称",
  "representative_quote": "最能代表该负面评价的原始文字片段（英文原文）",
  "summary": "一句话中文总结"
}

帖子列表（JSON数组）：
"""

ISSUE_SUBCATEGORY_PROMPT = """你是一个专业的用户反馈分析师。以下是来自 Snapmaker U1 3D打印机用户群的问题/求助帖子。

【重要】子分类必须遵循 MECE 原则：每个帖子只归入1个最主要的子类别。

问题/求助子类别（MECE，选其一）：
1. 工具头问题 (Toolhead Issues) - 拾取/停放失败、校准偏移、碰撞、加热异常
2. 打印质量问题 (Print Quality Issues) - 拉丝、层偏移、首层附着力、翘曲、表面缺陷
3. 机械结构问题 (Mechanical Issues) - 外壳松脱、导轨磨损、皮带噪音、风扇故障
4. 电气/连接问题 (Electrical/Connection) - WiFi断连、USB故障、电源问题、传感器失灵
5. 软件/固件问题 (Software/Firmware) - 切片软件BUG、固件更新问题、APP异常
6. 耗材问题 (Material Issues) - 耗材兼容性、堵料、送料异常、受潮
7. 使用咨询 (Usage Questions) - 设置方法、参数调整、功能咨询
8. 购买/配件咨询 (Purchase / Accessories) - 购买建议、配件推荐、兼容性咨询
9. 售后支持问题 (After-sales Support) - 客服响应、保修、退换货
10. 其他问题 (Other Issues) - 以上类别无法覆盖的问题

对每个帖子，返回JSON格式：
{
  "subcategory": "选择1个最主要的子类别名称",
  "representative_quote": "最能代表该问题的原始文字片段（英文原文）",
  "summary": "一句话中文总结"
}

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
                        {"role": "system", "content": "你是一个专业的用户反馈分析师，专注于3D打印机产品。请始终以JSON格式回复。"},
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
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        return json.loads(text)

    def classify_post(self, post_text: str) -> Dict:
        """Classify a single post into one of 5 primary categories."""
        prompt = PRIMARY_CLASSIFY_PROMPT + post_text[:2000]
        try:
            result_text = self._call_llm(prompt)
            result = self._parse_json_response(result_text)
            return result
        except (json.JSONDecodeError, Exception) as e:
            print(f"  Warning: Failed to parse LLM classification result: {e}")
            return {
                "category": "无意义",
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
        batch_size = 5  # Smaller batches for detailed analysis
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
