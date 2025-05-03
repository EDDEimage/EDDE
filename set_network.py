import argparse
import json
import random
import networkx as nx

class NetworkGenerator:
    def __init__(self, nodes=80, prob=0.1, bw=1000):
        self.node_count = nodes
        self.connect_prob = prob
        self.bandwidth = bw
        self.graph = None
        self.configs = []

    def create_topology(self):
        while True:
            G = nx.erdos_renyi_graph(self.node_count, self.connect_prob)
            if nx.is_connected(G):
                self.graph = G
                break
        return self.graph

    def _build_links(self):
        return {
            tuple(sorted(edge)): {
                "bw": self.bandwidth,
                "latency": random.choice([5,10])
            } for edge in self.graph.edges()
        }

    def generate_config(self):
        links = self._build_links()
        self.configs = []
        
        for node in range(self.node_count):
            neighbors = []
            for adj in self.graph.neighbors(node):
                link_key = tuple(sorted((node, adj)))
                params = links[link_key]
                
                neighbors.append({
                    "id": adj,
                    "ip": f"10.0.1.{adj+1}",
                    "bandwidth": params["bw"],
                    "latency": params["latency"]
                })

            self.configs.append({
                "node_id": node,
                "ip": f"10.0.1.{node+1}",
                "links": sorted(neighbors, key=lambda x: x["id"])
            })
        return self.configs

    def export_config(self, filename="net_config.json"):
        config = {
            "nodes": self.configs,
            "params": {
                "model": "ER",
                "base_bw": self.bandwidth,
                "latency_options": [5,10]
            }
        }
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        return filename

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--bandwidth", type=int, default=1000)
    parser.add_argument("-p", "--prob", type=float, default=0.1)
    parser.add_argument("-o", "--output", default="net_config.json")
    args = parser.parse_args()

    generator = NetworkGenerator(bw=args.bandwidth, prob=args.prob)
    generator.create_topology()
    generator.generate_config()
    output_file = generator.export_config(args.output)
    print(f"Configuration exported: {output_file}")

if __name__ == "__main__":
    main()