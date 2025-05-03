import docker
import yaml

def load_node_images(file_path):
    """
    Load the node and image information from the given file.
    """
    with open(file_path, 'r') as file:
        content = file.read()

    nodes = content.split('node ')
    node_images = {}
    for node_content in nodes1:]: 
        lines = node_content.strip().split('\n')
        node_id = lines]
        images = line.strip('[]') for line in lines:]]
        node_images[node_id] = images
    
    return node_images

def pull_images(node_images):
    """
    Pull images for each node using the Docker SDK.
    """
    client = docker.from_env()
    
    for node, images in node_images.items():
        print(f"Pulling images for node {node}...")
        for image in images:
            try:
                client.images.pull(image)
                print(f"Pulled image: {image}")
            except Exception as e:
                print(f"Failed to pull image {image}: {e}")

if __name__ == "__main__":
    file_path = 'image-distribution.txt'
    node_images = load_node_images(file_path)
    pull_images(node_images)