import os
import json
import random

FRAMES_DIR = "data/frames"
OUTPUT_JSON = "data/ordering.json"
NUM_FRAMES = 5  # 每个视频抽取多少帧

def compute_correct_order(frames, shuffled):
    """
    计算correct_order：对于frames中的每一帧，找到它在shuffled中的位置
    例如：
    frames = [1.jpg, 2.jpg, 3.jpg, 4.jpg, 5.jpg]
    shuffled = [3.jpg, 5.jpg, 1.jpg, 2.jpg, 4.jpg]
    则correct_order = [2,3,0,4,1]，因为:
    1.jpg在shuffled中位置2
    2.jpg在shuffled中位置3
    3.jpg在shuffled中位置0
    4.jpg在shuffled中位置4
    5.jpg在shuffled中位置1
    """
    # 创建从打乱后帧到其位置的映射
    frame_to_idx = {os.path.basename(f): i for i, f in enumerate(shuffled)}
    # 对于原始顺序中的每一帧，找到它在shuffled中的位置
    return [frame_to_idx[os.path.basename(f)] for f in frames]

def build_ordering_tasks():
    tasks = []
    # 对类别目录进行排序
    for category in sorted(os.listdir(FRAMES_DIR)):
        cat_path = os.path.join(FRAMES_DIR, category)
        if not os.path.isdir(cat_path):
            continue
        # 对视频目录进行排序
        for video in sorted(os.listdir(cat_path)):
            video_path = os.path.join(cat_path, video)
            if not os.path.isdir(video_path):
                continue

            frames = sorted(os.listdir(video_path))
            if len(frames) < NUM_FRAMES:
                continue

            # 均匀采样 NUM_FRAMES 帧
            step = len(frames) // NUM_FRAMES
            selected = [os.path.join(video_path, frames[i*step]) for i in range(NUM_FRAMES)]

            shuffled = selected[:]
            random.shuffle(shuffled)

            # 计算正确的排序顺序
            correct_order = compute_correct_order(selected, shuffled)

            tasks.append({
                "video": video,
                "frames": selected,
                "shuffled": shuffled,
                "correct_order": correct_order
            })

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(tasks, f, indent=2)

    print(f"生成 {len(tasks)} 个排序任务 -> {OUTPUT_JSON}")

if __name__ == "__main__":
    build_ordering_tasks()
