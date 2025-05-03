import subprocess
import time
import os
import shutil
import sys

# === Configuration ===
RUNTIMES = ['docker', 'nydus', 'gear', 'edde']  # 支持的运行时
IMAGE_NAME = "yolov7:latest"
PICTURE_DIR = "picture"  # 图片目录
OUTPUT_DIR = "results"  # 输出目录
BANDWIDTH_LIMIT = "500mbit"  # 带宽限制
NETWORK_INTERFACE = "eth0"  # 网络接口（根据实际环境修改）

# === Helper Functions ===
def check_image_exists(runtime):
    """检查镜像是否存在于本地"""
    try:
        subprocess.check_call([runtime, "images", "--filter", f"reference={IMAGE_NAME}", "--quiet"], stdout=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def pull_image(runtime):
    """拉取镜像"""
    print(f"[{runtime.upper()}] Pulling image...")
    start_time = time.time()
    subprocess.check_call([runtime, "pull", IMAGE_NAME])
    elapsed = time.time() - start_time
    print(f"[{runtime.upper()}] Image pulled in {elapsed:.2f} seconds")

def limit_bandwidth(interface, limit):
    """限制带宽（需 root 权限）"""
    print(f"[Bandwidth] Limiting {interface} to {limit}")
    subprocess.check_call(["tc", "qdisc", "add", "-p", "-u", "1:0", "handle", "1:0", "htb", "default", "12"])
    subprocess.check_call(["tc", "class", "add", "dev", interface, "parent", "1:0", "classid", "1:1", "htb", "rate", limit])
    subprocess.check_call(["tc", "qdisc", "add", "dev", interface, "parent", "1:1", "handle", "2:", "sfq"])

def reset_bandwidth(interface):
    """恢复带宽限制"""
    print(f"[Bandwidth] Resetting {interface}")
    subprocess.check_call(["tc", "qdisc", "del", "dev", interface, "root"])

def run_model(runtime, local=False):
    """运行 YOLOv7 模型并返回每张图片的处理时间"""
    if not local and not check_image_exists(runtime):
        pull_image(runtime)

    # 限制带宽（仅第一次运行时）
    if not local:
        limit_bandwidth(NETWORK_INTERFACE, BANDWIDTH_LIMIT)

    print(f"[{runtime.upper()}] Running model on {len(os.listdir(PICTURE_DIR))} images...")
    image_times = {}

    # 创建输出目录
    runtime_output_dir = os.path.join(OUTPUT_DIR, runtime)
    if os.path.exists(runtime_output_dir):
        shutil.rmtree(runtime_output_dir)
    os.makedirs(runtime_output_dir)

    # 逐个处理图片
    for image_name in sorted(os.listdir(PICTURE_DIR)):
        image_path = os.path.join(PICTURE_DIR, image_name)
        image_output_dir = os.path.join(runtime_output_dir, image_name.replace(".jpg", ""))
        os.makedirs(image_output_dir, exist_ok=True)

        start_time = time.time()

        # 构建命令（假设 detect.py 支持单张图片处理）
        cmd = [
            runtime, "run", "--rm",
            "-v", f"{os.path.abspath(image_path)}:/data",
            "-v", f"{os.path.abspath(image_output_dir)}:/results",
            IMAGE_NAME,
            "python3", "detect.py", "--source", "/data", "--output", "/results"
        ]
        subprocess.check_call(cmd)

        elapsed = time.time() - start_time
        image_times[image_name] = elapsed
        print(f"[{runtime.upper()}] Processed {image_name} in {elapsed:.2f} seconds")

    # 恢复带宽
    if not local:
        reset_bandwidth(NETWORK_INTERFACE)

    return image_times

# === Main Logic ===
if __name__ == "__main__":
    # 创建输出目录
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    results_first_run = {}
    results_second_run = {}

    for runtime in RUNTIMES:
        print(f"\n{'='*40}")
        print(f"Testing {runtime.upper()} - FIRST RUN (Image NOT Local)")
        results_first_run[runtime] = run_model(runtime, local=False)

        print(f"\n{'='*40}")
        print(f"Testing {runtime.upper()} - SECOND RUN (Image Local)")
        results_second_run[runtime] = run_model(runtime, local=True)

    # 输出结果
    print("\n" + "="*60)
    print("First Run Results (Image NOT Local):")
    for runtime, times in results_first_run.items():
        print(f"{runtime.upper()}:")
        for image, duration in times.items():
            print(f"  {image}: {duration:.2f} seconds")

    print("\nSecond Run Results (Image Local):")
    for runtime, times in results_second_run.items():
        print(f"{runtime.upper()}:")
        for image, duration in times.items():
            print(f"  {image}: {duration:.2f} seconds")