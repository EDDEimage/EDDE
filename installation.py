import os
import subprocess
import sys

# Define the path to the source folder containing the components
source_folder = './source'

# List of component names to install
components = ['gear', 'network', 'random']

def install_component(component_path):

    os.chdir(component_path)
    
    try:
        # Run setup.py to install the component
        subprocess.check_call([sys.executable, 'setup.py', 'install'])
        print(f"Successfully installed component: {component_path}")
    except Exception as e:
        print(f"Error occurred while installing component: {component_path}, Error: {e}")

if __name__ == "__main__":
    for component in components:
        component_path = os.path.join(source_folder, component)
        
        if os.path.exists(component_path):
            install_component(component_path)
        else:
            print(f"Component directory not found: {component_path}")