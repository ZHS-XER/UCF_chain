import cv2
from pathlib import Path


def extract_frames(video_path: Path, out_dir: Path, fps: int = 1, size=(224, 224)):
    """
    每秒抽取一帧并保存到 out_dir
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    interval = int(video_fps / fps) if video_fps >= fps else 1

    frame_idx = 0
    saved_idx = 1

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval == 0:
            frame_resized = cv2.resize(frame, size)
            out_file = out_dir / f"frame_{saved_idx:05d}.jpg"
            cv2.imwrite(str(out_file), frame_resized)
            saved_idx += 1
        frame_idx += 1

    cap.release()
    print(f"[完成] {video_path.stem}: 抽取 {saved_idx - 1} 帧 → {out_dir}")


if __name__ == "__main__":
    input_dir = Path("XER_UCF")  # 原始 UCF 视频目录（包含类别文件夹）
    output_dir = Path("data/frames")  # 输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 遍历类别文件夹
    for class_dir in input_dir.iterdir():
        if not class_dir.is_dir():
            continue
        class_name = class_dir.name
        print(f"\n>>> 开始处理类别: {class_name}")

        # 输出路径
        out_class_dir = output_dir / class_name
        out_class_dir.mkdir(parents=True, exist_ok=True)

        # 遍历视频文件
        for video_path in class_dir.glob("*.avi"):
            video_out = out_class_dir / video_path.stem
            extract_frames(video_path, video_out, fps=1, size=(224, 224))
