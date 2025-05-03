import subprocess
import time
from tabulate import tabulate

# 容器运行时列表及配置
RUNTIMES = ["docker", "nydus", "gear", "gear-eBPF", "gear-eBPF-image", "EDDE"]

# 容器镜像及参数配置
IMAGE_CONFIG = {
    "alpine": [],
    "ubuntu": [],
    "memcached": [],
    # ...其他镜像配置同原脚本
    "mysql": ["-e", "MYSQL_ROOT_PASSWORD=test"],
    # ...其他特殊配置
}

RUNTIME_COMMANDS = {
    "docker": {
        "run": ["docker", "run", "-d", "--rm", "--network"],
        "stop": ["docker", "stop"]
    },
    "nydus": {
        "run": ["nydusctl", "run", "--detach", "--network"],
        "stop": ["nydusctl", "stop"]
    },
    "gear": {
        "run": ["gear", "run", "--detached", "--network"],
        "stop": ["gear", "rm"]
    },
    "gear-eBPF": {
        "run": ["gear-ebpf", "launch", "--network"],
        "stop": ["gear-ebpf", "terminate"]
    },
    "gear-eBPF-image": {
        "run": ["gear-img", "start", "--net"],
        "stop": ["gear-img", "kill"]
    },
    "EDDE": {
        "run": ["edde", "container", "create", "--attach-network"],
        "stop": ["edde", "container", "destroy"]
    }
}

def setup_bandwidth(speed):
    """配置带宽限制"""
    try:
        # 创建Linux ifb接口
        subprocess.run(["sudo", "modprobe", "ifb"], check=True)
        subprocess.run(["sudo", "ip", "link", "set", "dev", "ifb0", "up"], check=True)
        
        # 设置流量控制规则
        subprocess.run([
            "sudo", "tc", "qdisc", "add", "dev", "eth0", "handle", "ffff:",
            "ingress"
        ], check=True)
        subprocess.run([
            "sudo", "tc", "filter", "add", "dev", "eth0", "parent", "ffff:",
            "protocol", "ip", "u32", "match", "u32", "0", "0",
            "action", "mirred", "egress", "redirect", "dev", "ifb0"
        ], check=True)
        subprocess.run([
            "sudo", "tc", "qdisc", "add", "dev", "ifb0", "root",
            "handle", "1:", "htb", "default", "30"
        ], check=True)
        subprocess.run([
            "sudo", "tc", "class", "add", "dev", "ifb0", "parent", "1:",
            "classid", "1:1", "htb", "rate", f"{speed}mbit"
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"带宽设置失败: {e.stderr.decode()}")
        return False

def cleanup_bandwidth():
    """清理带宽配置"""
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "eth0", "ingress"], 
                   stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "ifb0", "root"],
                   stderr=subprocess.DEVNULL)

def measure_deployment(runtime, image, speed):
    """测量容器启动时间"""
    params = IMAGE_CONFIG.get(image, [])
    cmd = RUNTIME_COMMANDS[runtime]["run"] + [f"net{speed}m"]
    cmd += params + [image]
    
    try:
        # 启动容器
        start_time = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # 获取容器ID（不同运行时适配）
        if runtime == "EDDE":
            container_id = proc.stdout.split("ContainerID:")[1].strip()
        else:
            container_id = proc.stdout.strip()
        
        # 计算启动耗时
        latency = time.perf_counter() - start_time
        
        # 停止容器
        stop_cmd = RUNTIME_COMMANDS[runtime]["stop"] + [container_id]
        subprocess.run(stop_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return round(latency, 2)
    except Exception as e:
        print(f"{runtime} 部署失败 {image}: {str(e)}")
        return None

def main():
    results = {rt: {50: {}, 500: {}} for rt in RUNTIMES}
    
    for speed in [50, 500]:
        if not setup_bandwidth(speed):
            continue
            
        for runtime in RUNTIMES:
            print(f"\n=== 正在测试 {runtime} @ {speed}Mbps ===")
            
            for img in IMAGE_CONFIG:
                # 运行三次取平均值
                timings = []
                for _ in range(3):
                    if duration := measure_deployment(runtime, img, speed):
                        timings.append(duration)
                    time.sleep(0.5)
                
                if timings:
                    avg_time = sum(timings)/len(timings)
                    results[runtime][speed][img] = round(avg_time, 2)
                else:
                    results[runtime][speed][img] = "N/A"
                
        cleanup_bandwidth()
    
    # 生成对比报表
    headers = ["容器镜像"] 
    for rt in RUNTIMES:
        headers.extend([f"{rt} 50M", f"{rt} 500M"])
    
    table = []
    for img in IMAGE_CONFIG:
        row = [img]
        for rt in RUNTIMES:
            row.append(results[rt][50].get(img, "N/A"))
            row.append(results[rt][500].get(img, "N/A"))
        table.append(row)
    
    print("\n测试结果对比：")
    print(tabulate(table, headers=headers, tablefmt="grid", stralign="center"))

if __name__ == "__main__":
    main()