import os
import random
import json

frames_dir = 'data/frames'
output_file = "questions.json"
question_data = []

for category in os.listdir(frames_dir):
    category_path = os.path.join(frames_dir, category)
    if not os.path.isdir(category_path):
        continue

    # 按 group (g01/g02/...) 组织
    groups = {}
    for video in os.listdir(category_path):
        if not video.startswith('v_'):
            continue
        parts = video.split('_')
        group = parts[2]  # g01 / g02 ...
        clip = parts[3]   # c01 / c02 ...
        if group not in groups:
            groups[group] = {}
        groups[group][clip] = os.path.join(category_path, video)

    # 遍历每个 group
    for group, clips in groups.items():
        if "c01" not in clips:
            continue

        c01_path = clips["c01"]
        frames = sorted(os.listdir(c01_path))
        if len(frames) < 2:
            continue

        # 题干：前3帧（不足则取2帧）
        head_frames = [os.path.join(c01_path, f) for f in frames[:3 if len(frames) > 3 else 2]]

        # 正确答案：最后一帧
        correct_frame = os.path.join(c01_path, frames[-1])

        # 错误答案：从同组其他 cXX 里随机抽 3 帧
        distractors = []
        other_clips = [c for c in clips if c != "c01"]
        for oc in other_clips:
            oc_path = clips[oc]
            oc_frames = os.listdir(oc_path)
            if not oc_frames:
                continue
            distractors.append(os.path.join(oc_path, random.choice(oc_frames)))
            if len(distractors) >= 3:
                break

        if len(distractors) < 3:
            continue

        choices = [correct_frame] + distractors
        random.shuffle(choices)
        correct_index = choices.index(correct_frame)

        question = {
            "category": category,
            "group": group,
            "head": head_frames,
            "choices": choices,
            "correct_index": correct_index
        }
        question_data.append(question)

# 保存 JSON
with open(output_file, "w") as f:
    json.dump(question_data, f, indent=2)

print(f"✅ 共生成 {len(question_data)} 道题，已保存到 {output_file}")