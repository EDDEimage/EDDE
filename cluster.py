import argparse
import json
import random
import networkx as nx
import matplotlib.pyplot as plt

class ClusterConfigurator:
    def __init__(self, node_count=80, connection_prob=0.1):
        self.node_count = node_count
        self.connection_prob = connection_prob
        self.graph = None

    def generate_er_graph(self):
        self.graph = nx.erdos_renyi_graph(n=self.node_count, p=self.connection_prob)
        for node in self.graph.nodes():
            self.graph.nodes[node]['ip'] = f"10.0.0.{node+1}"
            self.graph.nodes[node]['status'] = "active"
        return self.graph

    def get_connectivity_report(self):
        return {
            "is_connected": nx.is_connected(self.graph),
            "average_degree": sum(dict(self.graph.degree()).values()) / self.node_count,
            "cluster_coefficient": nx.average_clustering(self.graph),
            "diameter": nx.diameter(self.graph) if nx.is_connected(self.graph) else "N/A"
        }

    def save_config(self, filename="cluster_config.json"):
        config = {
            "metadata": {
                "model": "Erdős–Rényi",
                "node_count": self.node_count,
                "connection_probability": self.connection_prob
            },
            "nodes": [
                {
                    "id": node,
                    "ip": self.graph.nodes[node]['ip'],
                    "neighbors": list(self.graph.neighbors(node))
                } for node in self.graph.nodes()
            ],
            "connectivity_report": self.get_connectivity_report()
        }
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)

    def visualize(self, filename="cluster_graph.png"):
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.graph)
        nx.draw_networkx_nodes(self.graph, pos, node_size=200, node_color='lightblue')
        nx.draw_networkx_edges(self.graph, pos, alpha=0.4)
        nx.draw_networkx_labels(self.graph, pos, font_size=8)
        plt.title(f"Erdős–Rényi Cluster (n={self.node_count}, p={self.connection_prob})")
        plt.savefig(filename, dpi=300)
        plt.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--nodes", type=int, default=80)
    parser.add_argument("-p", "--probability", type=float, default=0.1)
    parser.add_argument("-o", "--output", default="cluster_config.json")
    parser.add_argument("-v", "--visualize", action="store_true")
    args = parser.parse_args()

    configurator = ClusterConfigurator(node_count=args.nodes, connection_prob=args.probability)
    print(" Generating random graph network...")
    graph = configurator.generate_er_graph()
    configurator.save_config(args.output)
    print(f" Configuration saved to {args.output}")

    if args.visualize:
        image_file = args.output.replace(".json", ".png")
        configurator.visualize(image_file)
        print(f" Network visualization saved to {image_file}")

    report = configurator.get_connectivity_report()
    print("\n Connectivity Report:")
    print(f"  Connected: {'Yes' if report['is_connected'] else 'No'}")
    print(f"  Average Degree: {report['average_degree']:.2f}")
    print(f"  Clustering Coefficient: {report['cluster_coefficient']:.4f}")
    print(f"  Diameter: {report['diameter']}")

if __name__ == "__main__":
    main()