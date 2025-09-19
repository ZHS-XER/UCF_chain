import os
import json
import re

RESULTS_DIR = "results_ordering"
SUMMARY_FILE = "ordering_summary.json"

def generate_summary():
    """生成排序任务的总结报告"""
    # 获取所有结果文件
    result_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.json')]
    print(f"找到 {len(result_files)} 个结果文件")

    # 初始化摘要数据
    summary = {
        "videos": [],
        "statistics": {
            "total": 0,
            "correct": 0,
            "accuracy": 0.0,
            "average_pairwise_accuracy": 0.0,
            "average_kendall_tau": 0.0
        },
        "category_statistics": {}  # 按类别统计正确率
    }

    # 用于计算平均值的累计变量
    total_pairwise_accuracy = 0.0
    total_kendall_tau = 0.0
    valid_predictions = 0

    # 记录跳过的文件
    skipped_files = []

    # 处理每个结果文件
    for result_file in sorted(result_files):
        file_path = os.path.join(RESULTS_DIR, result_file)
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                result = json.load(f)

                # 检查是否有必要的字段
                if not result.get("predicted_order") or not result.get("correct_order"):
                    print(f"跳过文件 {result_file}: 缺少必要字段 (predicted_order 或 correct_order)")
                    skipped_files.append(result_file)
                    continue

                # 提取关键信息
                video_name = result.get("video", result_file.replace(".json", ""))
                video_summary = {
                    "video": video_name,
                    "predicted_order": result.get("predicted_order"),
                    "correct_order": result.get("correct_order"),
                    "is_correct": result.get("is_correct", False)
                }

                # 添加配对评价指标
                if result.get("pairwise_metrics"):
                    metrics = result["pairwise_metrics"]
                    video_summary["pairwise_accuracy"] = metrics.get("pairwise_accuracy", 0.0)
                    video_summary["kendall_tau"] = metrics.get("kendall_tau", 0.0)

                    # 累计用于计算平均值
                    total_pairwise_accuracy += metrics.get("pairwise_accuracy", 0.0)
                    total_kendall_tau += metrics.get("kendall_tau", 0.0)
                    valid_predictions += 1

                # 添加到汇总
                summary["videos"].append(video_summary)

                # 更新总体统计信息
                if "is_correct" in result:
                    summary["statistics"]["total"] += 1
                    if result["is_correct"]:
                        summary["statistics"]["correct"] += 1

                # 更新类别统计信息
                # 从视频名称中提取类别 (v_Category_gXX_cXX)
                category = video_name.split('_')[1] if '_' in video_name else "Unknown"

                if category not in summary["category_statistics"]:
                    summary["category_statistics"][category] = {
                        "total": 0,
                        "correct": 0,
                        "accuracy": 0.0,
                        "total_pairwise_accuracy": 0.0,
                        "total_kendall_tau": 0.0,
                        "valid_predictions": 0,
                        "average_pairwise_accuracy": 0.0,
                        "average_kendall_tau": 0.0
                    }

                if "is_correct" in result:
                    summary["category_statistics"][category]["total"] += 1
                    if result["is_correct"]:
                        summary["category_statistics"][category]["correct"] += 1

                # 累计类别的配对指标
                if result.get("pairwise_metrics"):
                    metrics = result["pairwise_metrics"]
                    summary["category_statistics"][category]["total_pairwise_accuracy"] += metrics.get("pairwise_accuracy", 0.0)
                    summary["category_statistics"][category]["total_kendall_tau"] += metrics.get("kendall_tau", 0.0)
                    summary["category_statistics"][category]["valid_predictions"] += 1

            except json.JSONDecodeError as e:
                print(f"无法解析 {result_file}: {e}")
                skipped_files.append(result_file)
                continue
            except Exception as e:
                print(f"处理文件 {result_file} 时出错: {e}")
                skipped_files.append(result_file)
                continue

    # 报告跳过的文件
    if skipped_files:
        print(f"\n跳过了 {len(skipped_files)} 个文件:")
        for file in skipped_files:
            print(f"  - {file}")

    # 计算总体正确率和平均指标
    total = summary["statistics"]["total"]
    if total > 0:
        summary["statistics"]["accuracy"] = summary["statistics"]["correct"] / total

    if valid_predictions > 0:
        summary["statistics"]["average_pairwise_accuracy"] = total_pairwise_accuracy / valid_predictions
        summary["statistics"]["average_kendall_tau"] = total_kendall_tau / valid_predictions

    # 计算每个类别的正确率和平均指标
    for category, stats in summary["category_statistics"].items():
        if stats["total"] > 0:
            stats["accuracy"] = stats["correct"] / stats["total"]

        if stats["valid_predictions"] > 0:
            stats["average_pairwise_accuracy"] = stats["total_pairwise_accuracy"] / stats["valid_predictions"]
            stats["average_kendall_tau"] = stats["total_kendall_tau"] / stats["valid_predictions"]

        # 清理临时累计变量
        del stats["total_pairwise_accuracy"]
        del stats["total_kendall_tau"]
        del stats["valid_predictions"]

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
    print(f"平均配对准确率: {summary['statistics']['average_pairwise_accuracy']:.2%}")
    print(f"平均Kendall's tau: {summary['statistics']['average_kendall_tau']:.3f}")

    # 输出各类别正确率
    print("\n各类别统计:")
    for category, stats in sorted(summary["category_statistics"].items()):
        print(f"{category}: 严格匹配 {stats['correct']}/{stats['total']} ({stats['accuracy']:.2%}), "
              f"配对准确率 {stats['average_pairwise_accuracy']:.2%}, "
              f"Kendall's tau {stats['average_kendall_tau']:.3f}")

if __name__ == "__main__":
    generate_summary()
