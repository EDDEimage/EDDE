import subprocess
import time
import os
import sys

RUNTIMES = ['gear', 'gearebpf', 'edde']
IMAGE_NAME = "redis:7.2.0"
MONITOR_INTERVAL = 1
MONITOR_DURATION = 10

def deploy_container(runtime):
    container_name = f"redis_{runtime}"
    deploy_cmd = [runtime, "run", "-d", "--name", container_name, IMAGE_NAME]
    result = subprocess.run(deploy_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return None

    inspect_cmd = ["docker", "inspect", "--format", "{{.State.Pid}}", container_name] if runtime == "docker" else ["pgrep", "-f", container_name]
    pid_result = subprocess.run(inspect_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if pid_result.returncode != 0:
        return None

    return pid_result.stdout.strip()

def monitor_resources(pid, duration, interval):
    cpu_usage = []
    mem_usage = []
    end_time = time.time() + duration

    while time.time() < end_time:
        ps_cmd = ["ps", "-p", pid, "-o", "%cpu,%mem", "--no-headers"]
        result = subprocess.run(ps_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            try:
                cpu, mem = map(float, result.stdout.strip().split())
                cpu_usage.append(cpu)
                mem_usage.append(mem)
            except ValueError:
                pass
        time.sleep(interval)
    return cpu_usage, mem_usage

def stop_container(runtime, container_name):
    if runtime == "docker":
        stop_cmd = ["docker", "stop", container_name]
    else:
        stop_cmd = ["kill", "-9", container_name]
    subprocess.run(stop_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    results = {}

    for runtime in RUNTIMES:
        print(f"\n{'='*40}")
        print(f"Deploying Redis with {runtime.upper()}...")

        pid = deploy_container(runtime)
        if not pid:
            continue

        cpu_data, mem_data = monitor_resources(pid, MONITOR_DURATION, MONITOR_INTERVAL)
        stop_container(runtime, f"redis_{runtime}")

        results[runtime] = {
            "cpu": cpu_data,
            "mem": mem_data
        }

    print("\n" + "="*60)
    print("Resource Usage Results:")
    for runtime, data in results.items():
        avg_cpu = sum(data["cpu"]) / len(data["cpu"]) if data["cpu"] else 0
        avg_mem = sum(data["mem"]) / len(data["mem"]) if data["mem"] else 0
        print(f"\n{runtime.upper()}:")
        print(f"  Average CPU Usage: {avg_cpu:.2f}%")
        print(f"  Average Memory Usage: {avg_mem:.2f}%")
        print(f"  CPU Data (raw): {data['cpu']}")
        print(f"  Memory Data (raw): {data['mem']}")

    print("\n" + "="*60)
    print("Script completed.")