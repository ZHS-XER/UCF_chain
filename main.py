import os
import json
import asyncio
import re
from google import genai

API_KEY = "AIzaSyDajUbcHFWd--NuDXJ9ka5msNLlqjKhdeM"
client = genai.Client(api_key=API_KEY)

QUESTIONS_FILE = "questions.json"
RESULTS_DIR = "results_per_question"
os.makedirs(RESULTS_DIR, exist_ok=True)


async def ask_model(head, choices):
    """
    调用模型：
    - 对每一帧做描述
    - 给出思考过程
    - 给出选择题答案
    """
    head_str = "\n".join(head)
    choices_str = "\n".join([f"{i}: {c}" for i, c in enumerate(choices)])
    prompt = f"""
你是视频理解助手。
请对题干帧(head)做描述，并选择正确答案。
请严格按照下面格式输出：
<START_JSON>
{{
  "frame_descriptions": [
    "帧1描述",
    "帧2描述",
    "帧3描述"
  ],
  "reasoning": "详细思考过程",
  "pred": 答案编号(0-{len(choices)-1})
}}
<END_JSON>

题干帧:
{head_str}

候选答案帧:
{choices_str}
"""

    try:
        resp = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        text = resp.candidates[0].content.parts[0].text.strip()

        # 使用正则提取 JSON
        match = re.search(r"<START_JSON>(.*?)<END_JSON>", text, re.S)
        if match:
            json_text = match.group(1).strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        # 退化方案：直接把文本放在 reasoning，pred 为 None
        return {
            "frame_descriptions": [],
            "reasoning": text,
            "pred": None
        }

    except Exception as e:
        print(f"模型调用失败: {e}")
        return None


async def main():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    results_summary = []
    total = 0
    correct = 0

    for i, q in enumerate(questions):
        qid = f"{q['category']}_{q['group']}_{i}"
        output_file = os.path.join(RESULTS_DIR, f"{qid}.json")

        if os.path.exists(output_file):
            # Resume: 读取已有结果
            with open(output_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            print(f"{qid} 已存在，跳过")
        else:
            result = await ask_model(q["head"], q["choices"])
            if result is None:
                print(f"{qid} 调用失败，跳过")
                continue

            # 添加元信息
            result["qid"] = qid
            result["category"] = q["category"]
            result["group"] = q["group"]
            result["choices"] = q["choices"]
            result["correct_index"] = q["correct_index"]
            result["head"] = q["head"]

            # 保存单题 JSON
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"{qid} 已保存")

        # 记录正确与否
        is_correct = (result["pred"] == q["correct_index"])
        result["is_correct"] = is_correct
        results_summary.append(result)
        total += 1
        if is_correct:
            correct += 1
        print(f"{qid} -> 预测: {result['pred']} 正确答案: {q['correct_index']} {'正确' if is_correct else '错误'}")

    # 最终统计
    acc = correct / total if total > 0 else 0
    print(f"\n完成！总题目数: {total}, 正确数: {correct}, 准确率: {acc:.2%}")


if __name__ == "__main__":
    asyncio.run(main())