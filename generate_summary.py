import os
import json
import re

RESULTS_DIR = "results_ordering"
SUMMARY_FILE = "ordering_summary.json"

def generate_summary():
    """生成排序任务的总结报告"""
    # 获取所有结果文件
    result_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.json')]

    # 初始化摘要数据
    summary = {
        "videos": [],
        "statistics": {
            "total": 0,
            "correct": 0,
            "accuracy": 0.0
        }
    }

    # 处理每个结果文件
    for result_file in sorted(result_files):
        file_path = os.path.join(RESULTS_DIR, result_file)
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                result = json.load(f)

                # 提取关键信息
                video_summary = {
                    "video": result.get("video", result_file.replace(".json", "")),
                    "predicted_order": result.get("predicted_order"),
                    "correct_order": result.get("correct_order"),
                    "is_correct": result.get("is_correct", False)
                }

                # 添加到汇总
                summary["videos"].append(video_summary)

                # 更新统计信息
                if "is_correct" in result:
                    summary["statistics"]["total"] += 1
                    if result["is_correct"]:
                        summary["statistics"]["correct"] += 1

            except json.JSONDecodeError:
                print(f"无法解析 {result_file}")
                continue

    # 计算正确率
    total = summary["statistics"]["total"]
    if total > 0:
        summary["statistics"]["accuracy"] = summary["statistics"]["correct"] / total

    # 保存总结文件，使用自定义格式化确保数组在一行
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        # 使用 separators 和 compact 参数使输出更紧凑
        json_str = json.dumps(summary, ensure_ascii=False, indent=2, separators=(',', ': '))

        # 处理数组格式，使小数组在同一行
        # 匹配预测顺序和正确顺序数组
        pattern = r'(\s+)"(predicted_order|correct_order)": \[\s+([0-9,\s]+)\s+\]'

        # 将数组格式改为同一行
        def replace_array(match):
            indent = match.group(1)
            key = match.group(2)
            values = re.sub(r'\s+', ' ', match.group(3).strip())
            return f'{indent}"{key}": [{values}]'

        # 应用替换
        json_str = re.sub(pattern, replace_array, json_str)

        # 写入文件
        f.write(json_str)

    print(f"总结已保存到 {SUMMARY_FILE}")
    print(f"总正确率: {summary['statistics']['correct']}/{total} ({summary['statistics']['accuracy']:.2%})")

if __name__ == "__main__":
    generate_summary()
