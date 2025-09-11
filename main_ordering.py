import os
import json
import asyncio
import re
from google import genai

API_KEY = "AIzaSyDajUbcHFWd--NuDXJ9ka5msNLlqjKhdeM"
client = genai.Client(api_key=API_KEY)

ORDERING_FILE = "data/ordering.json"
RESULTS_DIR = "results_ordering"
os.makedirs(RESULTS_DIR, exist_ok=True)

async def ask_model_ordering(shuffled_frames):
    """
    调用模型进行帧排序：
    - 描述每一帧的内容
    - 分析动作的连续性
    - 预测正确的顺序
    """
    frame_prompts = [f"{i}: {os.path.basename(frame)}" for i, frame in enumerate(shuffled_frames)]
    prompt = f"""Here are 5 pictures from a video in shuffled order. Based on the picture numbers, predict their correct temporal order.

Frames:
{chr(10).join(frame_prompts)}

Please output your response in this format:
<START_JSON>
{{
  "frame_descriptions": [
    "detailed description for first picture",
    "detailed description for second picture",     
    "detailed description for third picture",
    "detailed description for fourth picture",
    "detailed description for fifth picture"
  ],
  "reasoning": "Explain your thought process for determining the correct order",
  "predicted_order": [x,x,x,x,x]
}}
<END_JSON>
"""

    try:
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = resp.candidates[0].content.parts[0].text.strip()

        # 提取JSON部分
        match = re.search(r"<START_JSON>(.*?)<END_JSON>", text, re.S)
        if match:
            json_text = match.group(1).strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        return {
            "frame_descriptions": [],
            "reasoning": text,
            "predicted_order": None
        }

    except Exception as e:
        print(f"模型调用失败: {e}")
        return None

async def process_video(video_name, task, stats):
    """处理单个视频的排序任务"""
    output_file = os.path.join(RESULTS_DIR, f"{video_name}.json")

    # 如果已经处理过，跳过
    if os.path.exists(output_file):
        print(f"{video_name} 已存在，跳过")
        with open(output_file, "r") as f:
            result = json.load(f)
            if result.get("is_correct"):
                stats["correct"] += 1
            stats["total"] += 1
        return

    print(f"\n处理 {video_name} ...")

    result = await ask_model_ordering(task["shuffled"])
    if result is None:
        print(f"{video_name} 调用失败")
        return

    # 添加任务信息
    result["video"] = video_name
    result["shuffled_frames"] = task["shuffled"]
    result["correct_order"] = task["correct_order"]

    # 判断是否正确
    is_correct = False
    if result.get("predicted_order"):
        is_correct = (result["predicted_order"] == task["correct_order"])
        result["is_correct"] = is_correct

        # 更新统计
        stats["total"] += 1
        if is_correct:
            stats["correct"] += 1

        # 输出当前结果
        print(f"预测顺序: {result['predicted_order']}")
        print(f"正确顺序: {task['correct_order']}")
        print(f"结果: {'✓' if is_correct else '✗'}")
        print(f"当前正确率: {stats['correct']}/{stats['total']} ({stats['correct']/stats['total']:.2%})")

    # 保存结果
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

async def main():
    # 读取排序任务
    with open(ORDERING_FILE, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    # 统计结果
    stats = {"total": 0, "correct": 0}

    # 处理每个视频
    for task in tasks:
        await process_video(task["video"], task, stats)

    # 输出最终统计信息
    if stats["total"] > 0:
        print(f"\n完成！最终正确率: {stats['correct']}/{stats['total']} ({stats['correct']/stats['total']:.2%})")


if __name__ == "__main__":
    asyncio.run(main())