#!/usr/bin/env python3
import subprocess
import time
import os
import glob
import pandas as pd
from datetime import datetime
from collections import defaultdict


METHODS = ["Topo-image", "BF-image", "BF-image-dup"]
BANDWIDTHS = [50, 500]  
TARGET_IMAGE = "redis:7.2.0"
DEVICE = "nvme0n1"  # 根据实际存储设备修改
BLKTRACE_DIR = "./blktrace_data"
RUNS = 3


METHOD_COMMANDS = {
    "Topo-image": ["puller", "run", "--method=topo"],
    "BF-image": ["puller", "run", "--method=bf"],
    "BF-image-dup": ["puller", "run", "--method=bf-dup"]
}

def setup_environment():
 
    os.makedirs(BLKTRACE_DIR, exist_ok=True)
    subprocess.run(["sudo", "rmmod", "ifb"], stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "modprobe", "ifb"], check=True)
    subprocess.run(["sudo", "ip", "link", "set", "dev", "ifb0", "up"], check=True)

def configure_bandwidth(speed):
 
    try:
   
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "eth0", "root"], 
                      stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "ifb0", "root"],
                      stderr=subprocess.DEVNULL)

   
        subprocess.run([
            "sudo", "tc", "qdisc", "add", "dev", "eth0", "root", 
            "handle", "1:", "htb", "default", "1"
        ], check=True)
        subprocess.run([
            "sudo", "tc", "class", "add", "dev", "eth0", "parent", "1:",
            "classid", "1:1", "htb", "rate", f"{speed}mbit"
        ], check=True)

       
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
            "handle", "1:", "htb", "default", "1"
        ], check=True)
        subprocess.run([
            "sudo", "tc", "class", "add", "dev", "ifb0", "parent", "1:",
            "classid", "1:1", "htb", "rate", f"{speed}mbit"
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"带宽配置失败: {e.stderr.decode()}")
        return False

def run_blktrace(start_event, output_prefix):
 
    blktrace_proc = subprocess.Popen([
        "sudo", "blktrace", "-d", f"/dev/{DEVICE}", 
        "-o", output_prefix, "-a", "read", "-a", "write"
    ])
    start_event.set()
    return blktrace_proc

def parse_blktrace(output_prefix):
   
    files = glob.glob(f"{output_prefix}*.blktrace*")
    if not files:
        return None


    merge_proc = subprocess.Popen([
        "sudo", "blkparse", "-i", output_prefix, "-o", f"{output_prefix}.merged"
    ])
    merge_proc.wait()


    timeline = []
    with open(f"{output_prefix}.merged") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 12:
                continue
            timestamp = float(parts[3].strip('[]'))
            sector = int(parts[7])
            size = int(parts[9]) * 512  
            op_type = parts[5][0]
            timeline.append((timestamp, sector, size, op_type))
    
    return timeline

def analyze_io_pattern(timeline):
    
    file_map = defaultdict(list)
    current_files = {}
    
   
    with subprocess.Popen(["sudo", "xfs_db", "-r", f"/dev/{DEVICE}", "-c", "inode -n", "-c", "blockget -n"], 
                         stdout=subprocess.PIPE, text=True) as proc:
        for line in proc.stdout:
            if "inode" in line and "extents:" in line:
                inode = line.split()[1]
                extents = []
            elif "extent" in line:
                parts = line.split()
                start = int(parts[3])
                blocks = int(parts[5])
                extents.append((start, blocks))
                current_files[inode] = extents
    
    
    for ts, sector, size, op_type in timeline:
        for inode, extents in current_files.items():
            for (start, blocks) in extents:
                end_sector = start + blocks*8  # 转换为512B sectors
                if start <= sector < end_sector:
                    file_map[inode].append((ts, op_type, size))
                    break
    return file_map

def run_experiment(method, speed, run_id):
    
    output_prefix = f"{BLKTRACE_DIR}/{method}_{speed}Mbps_run{run_id}"
    
    
    blktrace_proc = run_blktrace(output_prefix)
    

    start_time = time.time()
    cmd = METHOD_COMMANDS[method] + [TARGET_IMAGE]
    container_proc = subprocess.run(cmd, capture_output=True, text=True)
    

    if container_proc.returncode == 0:
        container_id = container_proc.stdout.strip()
        while True:
            status = subprocess.run(
                ["puller", "status", container_id],
                capture_output=True, text=True
            )
            if "RUNNING" in status.stdout:
                break
            time.sleep(0.1)
    
  
    blktrace_proc.terminate()
    blktrace_proc.wait()
    
 
    timeline = parse_blktrace(output_prefix)
    if not timeline:
        return None
    
    io_map = analyze_io_pattern(timeline)
    return io_map

def main():
    setup_environment()
    results = defaultdict(lambda: defaultdict(list))
    
    for method in METHODS:
        for speed in BANDWIDTHS:
            if not configure_bandwidth(speed):
                continue
            
            for run in range(RUNS):
                               io_data = run_experiment(method, speed, run)
                
                if io_data:
                    for inode, ops in io_data.items():
                        start = min(op[0] for op in ops)
                        end = max(op[0] for op in ops)
                        results[(method, speed)][inode].append(end - start)
                
                time.sleep(2)  
    

    report = []
    for (method, speed), inode_data in results.items():
        for inode, durations in inode_data.items():
            avg_time = sum(durations)/len(durations)
            report.append({
                "Method": method,
                "Bandwidth(Mbps)": speed,
                "Inode": inode,
                "AvgTime(s)": round(avg_time, 3),
                "MinTime(s)": round(min(durations), 3),
                "MaxTime(s)": round(max(durations), 3)
            })
    
    df = pd.DataFrame(report)
    pivot_table = df.pivot_table(
        index=["Inode", "Bandwidth(Mbps)"],
        columns="Method",
        values="AvgTime(s)",
        aggfunc='first'
    )
    
 
    print(pivot_table.to_markdown())
    
   
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    df.to_csv(f"result_{timestamp}.csv", index=False)

if __name__ == "__main__":
    main()