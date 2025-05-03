import re
from collections import defaultdict

NODE_COUNT = 80

def parse_distribution(file_path):

    images = {}
    unit_map = {'KB': 1024, 'MB': 1024&zwnj;**2, 'GB': 1024**&zwnj;3, 'TB': 1024**4}
    
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            

            match = re.match(r"^(\S+)\s+nodes=(\d+)\s+(.+)$", line)
            if not match:
                continue
                
            name = match.group(1)
            nodes = int(match.group(2))
            layers_str = match.group(3)
            
           
            layers = {}
            for part in layers_str.split():
                layer_match = re.match(r"(\w+)=([\d.]+)([KMGT]?B)", part)
                if not layer_match:
                    continue
                    
                layer_name = layer_match.group(1)
                value = float(layer_match.group(2))
                unit = layer_match.group(3).upper()
                bytes_size = int(value * unit_map[unit])
                
                layers[layer_name] = bytes_size
                
            images[name] = {
                'nodes': nodes,
                'layers': layers,
                'total_size': sum(layers.values())
            }
            
    return images

def calculate_storage(images, hybrid_traditional=[]):
   
    global_layers = defaultdict(int)
    
    
    hybrid_layers = set()
    
    
    results = {
        'Conventional': 0,
        'Hybrid': 0,
        'EDDE': 0
    }
    
   
    for img_info in images.values():
        for layer, size in img_info['layers'].items():
            if global_layers[layer] < size:
                global_layers[layer] = size
    

    results['EDDE'] = sum(global_layers.values())
    
    
    for name, img_info in images.items():
        nodes = img_info['nodes']
        total_size = img_info['total_size']
        
       
        results['Conventional'] += total_size * nodes
        
     
        if name in hybrid_traditional:
           
            results['Hybrid'] += total_size * nodes
            hybrid_layers.update(img_info['layers'].keys())
        else:
            
            pass  
    
   
    hybrid_storage = results['Hybrid'] + sum(
        size for layer, size in global_layers.items()
        if layer not in hybrid_layers
    )
    results['Hybrid'] = hybrid_storage
    
    return results

def format_size(size_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_idx = 0
    while size_bytes >= 1024 and unit_idx < len(units)-1:
        size_bytes /= 1024
        unit_idx += 1
    return f"{size_bytes:.2f} {units[unit_idx]}"

if __name__ == "__main__":
    
    INPUT_FILE = "image-distribution.txt"
    HYBRID_TRADITIONAL = ["base-os", "common-libs"]  # 指定使用传统部署的镜像
    
  
    images = parse_distribution(INPUT_FILE)
    
    
    total_nodes = sum(img['nodes'] for img in images.values())
    if total_nodes != NODE_COUNT:
        print(f"警告：总节点数不一致（配置{NODE_COUNT}，实际{total_nodes}）")
    
    
    results = calculate_storage(images, HYBRID_TRADITIONAL)
   
    for strategy in ['Conventional', 'Hybrid', 'EDDE']:
        print(f"{strategy:>12}: {format_size(results[strategy])}")