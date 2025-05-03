from setuptools import setup
from setuptools.command.install import install
import subprocess
import sys

class MakeInstall(install):
    def run(self):
        # Run 'make' command to build and install components
        try:
            print("Running 'make' to build and install components...")
            subprocess.check_call(['make'])
            
            # Optionally, call a specific target like 'make install'
            # subprocess.check_call(['make', 'install'])

            print("Successfully built and installed components using Makefile.")
        except Exception as e:
            print(f"Error occurred while running 'make': {e}")
            raise

# Package metadata
setup(
    name='my_components',
    version='0.1',
    description='A package that uses a Makefile to build and install components.',
    cmdclass={
        'install': MakeInstall,
    },
)
🛠️ Usage 