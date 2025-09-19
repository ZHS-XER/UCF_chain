#!/usr/bin/env python3
"""
修复不完整的JSON结果文件
检查results_ordering目录中的所有JSON文件，找到不完整的文件并重新处理
"""

import os
import json
import asyncio
from main_ordering import ask_model_ordering, calculate_pairwise_accuracy

ORDERING_FILE = "data/ordering.json"
RESULTS_DIR = "results_ordering"

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

def check_json_completeness(file_path):
    """检查JSON文件是否完整"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            result = json.load(f)

        # 检查关键字段是否存在且完整
        predicted_order = result.get("predicted_order")
        correct_order = result.get("correct_order")

        if not predicted_order or not correct_order:
            return False, "缺少predicted_order或correct_order字段"

        if not isinstance(predicted_order, list) or len(predicted_order) != 5:
            return False, f"predicted_order不完整，长度为{len(predicted_order) if isinstance(predicted_order, list) else 'unknown'}"

        if not isinstance(correct_order, list) or len(correct_order) != 5:
            return False, f"correct_order不完整，长度为{len(correct_order) if isinstance(correct_order, list) else 'unknown'}"

        return True, "完整"

    except json.JSONDecodeError as e:
        return False, f"JSON解析错误: {e}"
    except Exception as e:
        return False, f"其他错误: {e}"

async def ask_model_ordering_with_retry(video_name, shuffled_frames, max_retries=MAX_RETRIES):
    """带重试机制的模型调用"""
    for attempt in range(max_retries):
        try:
            result = await ask_model_ordering(video_name, shuffled_frames)
            if result and result.get("predicted_order") is not None:
                return result
            else:
                print(f"  尝试 {attempt + 1}/{max_retries} - 输出格式不完整，等待重试...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"  尝试 {attempt + 1}/{max_retries} - 调用失败: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)

    print(f"  经过 {max_retries} 次尝试仍然失败")
    return None

async def fix_incomplete_file(video_name, task):
    """重新处理不完整的文件"""
    print(f"重新处理 {video_name}...")

    result = await ask_model_ordering_with_retry(video_name, task["shuffled"])
    if result is None:
        print(f"  {video_name} 重新处理失败")
        return False

    # 添加任务信息
    result["video"] = video_name
    result["shuffled_frames"] = task["shuffled"]
    result["correct_order"] = task["correct_order"]

    # 判断是否正确
    if result.get("predicted_order"):
        is_correct = (result["predicted_order"] == task["correct_order"])
        result["is_correct"] = is_correct

        # 计算配对评价指标
        pairwise_metrics = calculate_pairwise_accuracy(result["predicted_order"], task["correct_order"])
        result["pairwise_metrics"] = pairwise_metrics

        print(f"  预测顺序: {result['predicted_order']}")
        print(f"  正确顺序: {task['correct_order']}")
        print(f"  严格匹配: {'✓' if is_correct else '✗'}")

    # 保存结果
    output_file = os.path.join(RESULTS_DIR, f"{video_name}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  {video_name} 修复完成")
    return True

async def main():
    # 读取排序任务
    with open(ORDERING_FILE, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    # 创建视频名到任务的映射
    task_map = {task["video"]: task for task in tasks}

    # 检查所有结果文件
    result_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.json')]
    incomplete_files = []

    print(f"检查 {len(result_files)} 个结果文件...")

    for result_file in sorted(result_files):
        file_path = os.path.join(RESULTS_DIR, result_file)
        is_complete, reason = check_json_completeness(file_path)

        if not is_complete:
            video_name = result_file.replace('.json', '')
            incomplete_files.append((video_name, reason))
            print(f"发现不完整文件: {result_file} - {reason}")

    if not incomplete_files:
        print("所有文件都是完整的！")
        return

    print(f"\n发现 {len(incomplete_files)} 个不完整的文件，开始修复...")

    # 修复不完整的文件
    fixed_count = 0
    for video_name, reason in incomplete_files:
        if video_name in task_map:
            success = await fix_incomplete_file(video_name, task_map[video_name])
            if success:
                fixed_count += 1
        else:
            print(f"警告: 找不到 {video_name} 对应的任务数据")

    print(f"\n修复完成！成功修复 {fixed_count}/{len(incomplete_files)} 个文件")

if __name__ == "__main__":
    asyncio.run(main())
