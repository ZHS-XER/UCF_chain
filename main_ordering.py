import os
import json
import asyncio
import re
import random
import string
from google import genai
from PIL import Image
import base64
import io

API_KEY = "AIzaSyBArpfiWV5eKCPRGU9rVKeMdtcfQYyHV6U"
client = genai.Client(api_key=API_KEY)

ORDERING_FILE = "data/ordering.json"
RESULTS_DIR = "results_ordering"
os.makedirs(RESULTS_DIR, exist_ok=True)

def encode_image(image_path):
    """将图片编码为base64"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"图片编码失败 {image_path}: {e}")
        return None

async def ask_model_ordering(video_name, shuffled_frames):
    """
    调用模型进行帧排序：
    - 描述每一帧的内容
    - 分析动作的连续性
    - 预测正确的顺序
    """
    # 创建随机标识符替代真实文件名，防止模型从文件名推断顺序
    random_ids = [f"frame_{i}" for i in range(len(shuffled_frames))]

    # 直接使用完整路径，shuffled_frames 中已包含完整路径
    image_paths = shuffled_frames

    # 确保所有图片都存在
    for path in image_paths:
        if not os.path.exists(path):
            print(f"图片不存在: {path}")
            return None

    # 准备图片内容
    images = []
    for i, path in enumerate(image_paths):
        encoded = encode_image(path)
        if encoded:
            images.append({
                "mime_type": "image/jpeg",
                "data": encoded
            })

    if len(images) != len(shuffled_frames):
        print(f"有些图片无法编码，跳过任务")
        return None

    # 构建提示
    text_prompt = f"""Here are {len(shuffled_frames)} pictures from a video in shuffled order. Predict their correct temporal order.

Please output your response in this format:
<START_JSON>
{{
  "frame_descriptions": [
    "detailed description for first picture (frame_0)",
    "detailed description for second picture (frame_1)",
    "detailed description for third picture (frame_2)",
    "detailed description for fourth picture (frame_3)",
    "detailed description for fifth picture (frame_4)"
  ],
  "reasoning": "Explain your thought process for determining the correct order",
  "predicted_order": [x,x,x,x,x]
}}
<END_JSON>

The predicted_order should be a list of indices (0-4) indicating the temporal sequence.
"""

    try:
        # 构建完整的请求内容
        contents = [{"text": text_prompt}]

        # 添加图片，并标记每张图片
        for i, img in enumerate(images):
            contents.append({"text": f"\nframe_{i}:"})
            contents.append({"inline_data": img})

        # 调用模型
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-pro",
            contents=contents
        )
        text = resp.candidates[0].content.parts[0].text.strip()

        # 提取JSON部分
        match = re.search(r"<START_JSON>(.*?)<END_JSON>", text, re.S)
        if match:
            json_text = match.group(1).strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                print(f"JSON解析失败: {json_text}")
                return {
                    "frame_descriptions": [],
                    "reasoning": text,
                    "predicted_order": None
                }
        else:
            print(f"未找到JSON格式输出")
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

    result = await ask_model_ordering(video_name, task["shuffled"])
    if result is None:
        print(f"{video_name} 调用失败")
        return

    # 添加任务信息
    result["video"] = video_name
    result["shuffled_frames"] = task["shuffled"]
    result["correct_order"] = task["correct_order"]

    # 判断是否正确
    is_correct = False
    pairwise_metrics = None
    if result.get("predicted_order"):
        is_correct = (result["predicted_order"] == task["correct_order"])
        result["is_correct"] = is_correct

        # 计算配对评价指标
        pairwise_metrics = calculate_pairwise_accuracy(result["predicted_order"], task["correct_order"])
        result["pairwise_metrics"] = pairwise_metrics

        # 更新统计
        stats["total"] += 1
        if is_correct:
            stats["correct"] += 1

        # 输出当前结果
        print(f"预测顺序: {result['predicted_order']}")
        print(f"正确顺序: {task['correct_order']}")
        print(f"严格匹配: {'✓' if is_correct else '✗'}")
        if pairwise_metrics:
            print(f"配对准确率: {pairwise_metrics['pairwise_accuracy']:.2%}")
            print(f"Kendall's tau: {pairwise_metrics['kendall_tau']:.3f}")
        print(f"当前正确率: {stats['correct']}/{stats['total']} ({stats['correct']/stats['total']:.2%})")

    # 保存结果
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def calculate_pairwise_accuracy(predicted_order, correct_order):
    """
    计算基于元素对相对顺序的准确率和Kendall's tau系数

    Args:
        predicted_order: 预测的排序，如 [0, 1, 2, 3, 4]
        correct_order: 正确的排序，如 [0, 1, 3, 2, 4]

    注意：这里的顺序表示的是在每个位置上应该放置哪个元素

    Returns:
        dict: 包含一致对数、不一致对数、总对数、配对准确率和Kendall's tau的字典
    """
    if not predicted_order or not correct_order or len(predicted_order) != len(correct_order):
        return {
            "concordant_pairs": 0,
            "discordant_pairs": 0,
            "total_pairs": 0,
            "pairwise_accuracy": 0.0,
            "kendall_tau": 0.0
        }

    n = len(predicted_order)
    concordant_pairs = 0  # 一致对数
    discordant_pairs = 0  # 不一致对数
    total_pairs = 0

    # 遍历所有可能的位置对 (pos_i, pos_j)，其中 pos_i < pos_j
    for pos_i in range(n):
        for pos_j in range(pos_i + 1, n):
            total_pairs += 1

            # 在正确顺序中，pos_i位置的元素应该在pos_j位置的元素之前
            correct_elem_i = correct_order[pos_i]  # 在pos_i位置的正确元素
            correct_elem_j = correct_order[pos_j]  # 在pos_j位置的正确元素

            # 在预测顺序中找到这两个元素的位置
            pred_pos_i = predicted_order.index(correct_elem_i)
            pred_pos_j = predicted_order.index(correct_elem_j)

            # 检查在预测顺序中，这两个元素的相对顺序是否正确
            if pred_pos_i < pred_pos_j:
                concordant_pairs += 1  # 一致
            else:
                discordant_pairs += 1  # 不一致

    # 计算配对准确率
    pairwise_accuracy = concordant_pairs / total_pairs if total_pairs > 0 else 0.0

    # 计算Kendall's tau: τ = (一致对数 - 不一致对数) / 总对数
    kendall_tau = (concordant_pairs - discordant_pairs) / total_pairs if total_pairs > 0 else 0.0

    return {
        "concordant_pairs": concordant_pairs,
        "discordant_pairs": discordant_pairs,
        "total_pairs": total_pairs,
        "pairwise_accuracy": pairwise_accuracy,
        "kendall_tau": kendall_tau
    }

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
