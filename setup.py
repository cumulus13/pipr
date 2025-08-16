from setuptools import setup, find_packages
from pathlib import Path
import shutil

NAME = 'pipr'
shutil.copy('__version__.py', str(Path(NAME) / '__version__.py'))

def get_version():
    try:
        with open(f"{NAME.replace('-', '_')}/__version__.py", "r") as f:
             for line in f:
                 if line.strip().startswith("version"):
                     parts = line.split("=")
                     if len(parts) == 2:
                         return parts[1].strip().strip('"').strip("'")
    except Exception as e:
        print(f"Error getting version: {e}")
    return "0.1"

def requirements():
    try:
        with open('requirements.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading requirements: {e}")
    return []

setup(
    name=NAME,
    version=get_version(),
    packages=[NAME.replace("-","_")],
    include_package_data=True,
    install_requires=requirements(),
    entry_points={
        'console_scripts': [
            f'pipr = {NAME}.pipr:main',
        ],
    },
    author="Hadi Cahyadi",
    author_email="cumulus13@gmail.com",
    description="Python Package Requirements Checker",
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf-8") if Path("README.md").exists() else "",
    long_description_content_type="text/markdown",
    url="https://github.com/cumulus13/pipr",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    python_requires='>=3.7',
    license="MIT",
)
