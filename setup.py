from setuptools import setup, find_packages, Extension
from setuptools.dist import Distribution
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist
import sys
from pathlib import Path
import shutil
import os
import re
import hashlib

NAME = 'pipr'
shutil.copy2('__version__.py', str(Path(NAME) / '__version__.py'))

# Custom build_py to exclude .py files when building with Cython
class BuildPyExcludeSource(build_py):
    """Custom build_py that excludes source .py files for cythonized modules"""
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        if hasattr(self.distribution, 'ext_modules') and self.distribution.ext_modules:
            return [
                (pkg, module, filename) 
                for pkg, module, filename in modules
                if module != 'pipr'  # Exclude pipr.py since we have pipr.pyd/.so
            ]
        return modules

# Custom sdist command to include pre-compiled binaries
class SdistWithBinaries(sdist):
    """Custom sdist that includes pre-compiled .so/.pyd files"""
    
    def make_release_tree(self, base_dir, files):
        """Create release tree and add compiled binaries"""
        super().make_release_tree(base_dir, files)
        
        # After creating the release tree, copy any compiled binaries
        print("\nAdding pre-compiled binaries to sdist...")
        
        # Find all .so and .pyd files in the build directory
        binary_patterns = [
            'build/**/*.so',
            'build/**/*.pyd',
            f'{NAME}/**/*.so',
            f'{NAME}/**/*.pyd',
        ]
        
        binaries_found = []
        for pattern in binary_patterns:
            binaries_found.extend(glob.glob(pattern, recursive=True))
        
        # Copy binaries to sdist
        for binary in binaries_found:
            # Determine relative path
            if binary.startswith('build/'):
                # Extract path after build/lib*/
                parts = binary.split(os.sep)
                try:
                    lib_idx = next(i for i, p in enumerate(parts) if p.startswith('lib'))
                    rel_path = os.path.join(*parts[lib_idx + 1:])
                except (StopIteration, IndexError):
                    rel_path = os.path.basename(binary)
            else:
                rel_path = binary
            
            dest = os.path.join(base_dir, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            
            if os.path.exists(binary):
                shutil.copy2(binary, dest)
                print(f"  ✓ Added: {rel_path}")
        
        if binaries_found:
            print(f"✅ Added {len(binaries_found)} binary file(s) to sdist")
        else:
            print("⚠️  No pre-compiled binaries found - sdist will require compilation")


class BinaryDistribution(Distribution):
    """Distribution which always forces a binary package with platform name"""
    def has_ext_modules(foo):
        return True

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

def calculate_file_hash(filepath):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return None

_extensions = []
extensions = None
cmdclass = {}

# Try to build Cython extensions
try:
    from Cython.Build import cythonize
    
    print("Preparing Cython compilation...")

    # Define file paths
    pipr_py = 'pipr/pipr.py'
    pipr_pyx = 'pipr/pipr.pyx'
    
    # Check if both files exist and compare hashes
    py_hash = calculate_file_hash(pipr_py)
    pyx_hash = calculate_file_hash(pipr_pyx)
    
    # If hashes are different or .pyx doesn't exist, copy .py to .pyx
    if py_hash != pyx_hash:
        if py_hash is not None:  # Source file exists
            print(f"Copying {pipr_py} -> {pipr_pyx} (hash mismatch or missing .pyx)")
            shutil.copy2(pipr_py, pipr_pyx)
        else:
            print(f"Warning: Source file {pipr_py} not found")
    
    _extensions = [
        Extension(
            'pipr.pipr', 
            ['pipr/pipr.pyx'],
            extra_compile_args=['/O2'] if sys.platform == 'win32' else ['-O3'],
        ),
    ]
    
    extensions = cythonize(
        _extensions,
        compiler_directives={
            'language_level': '3',
            'embedsignature': True,
            'boundscheck': False,
            'wraparound': False,
        }
    )
    
    # Use custom build_py to exclude source files from wheels
    cmdclass['build_py'] = BuildPyExcludeSource
    
    # Use custom sdist to include binaries
    cmdclass['sdist'] = SdistWithBinaries
    
    # MANIFEST.in for Cython build
    with open('MANIFEST.in', 'w') as fm:
        fm.write("""include README.md
include __version__.py
include LICENSE*

# Include package metadata files
include pipr/__init__.py
include pipr/__version__.py

# Include pre-compiled binaries in sdist
recursive-include pipr *.so
recursive-include pipr *.pyd
recursive-include build *.so
recursive-include build *.pyd

# Include images
recursive-include pipr *.png

# Exclude source files from binary wheels (but keep in sdist)
global-exclude *.py[cod]
global-exclude __pycache__
global-exclude .git*
global-exclude *.ini
global-exclude *.c
global-exclude *.1
global-exclude *.2
global-exclude *.0
global-exclude bck/

# For sdist, we want binaries; for bdist_wheel, exclude source
prune pipr/pipr.py
prune pipr/pipr.pyx
""")
    
    print("✓ Cython extensions configured successfully")
    print("✓ Binary wheels will exclude .py/.pyx/.c files")
    print("✓ Sdist will include pre-compiled .so/.pyd files if available")
        
except ImportError as e:
    print(f"✗ Cython not installed: {e}")
    print("  Install with: pip install cython")
    print("  Building without Cython extensions - source files will be included")
    
    with open('MANIFEST.in', 'w') as fm:
        fm.write("""include README.md
include __version__.py
recursive-include pipr *.py
recursive-include pipr *.png
include pipr/__init__.py
include pipr/__version__.py

global-exclude *.py[cod]
global-exclude __pycache__
global-exclude .git*
global-exclude *.ini
global-exclude *.1
global-exclude *.0
global-exclude *.2
global-exclude bck/
global-exclude *.c

include LICENSE*
""")

except Exception as e:
    print(f"✗ Cython build failed: {e}")
    print("  Building without Cython extensions - source files will be included")
    if os.getenv('TRACEBACK', '0').lower() in ['1', 'true', 'yes']:
        print(traceback.format_exc())
    
    with open('MANIFEST.in', 'w') as fm:
        fm.write("""include README.md
include __version__.py
recursive-include pipr *.py
recursive-include pipr *.png
include pipr/__init__.py
include pipr/__version__.py

global-exclude *.py[cod]
global-exclude __pycache__
global-exclude .git*
global-exclude *.ini
global-exclude *.1
global-exclude *.0
global-exclude *.2
global-exclude bck/
global-exclude *.c

include LICENSE*
""")

setup(
    name=NAME,
    version=get_version(),
    packages=[NAME.replace("-","_")],
    include_package_data=True,
    install_requires=requirements(),
    extras_require={
        "color": [
            "richcolorlog",
        ],
        "requests": [
            "requests",
        ],
        "request": [
            "requests",
        ],
        "rich": [
            "rich>=10.0.0",
        ]
    },
    entry_points={
        'console_scripts': [
            f'pipr = {NAME}.__main__:main',
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
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    python_requires='>=3.7',
    license="MIT",
    package_data={
        'pipr': ['*.png', f'*{sys.version_info.major}{sys.version_info.minor}*.pyd'] if sys.platform == 'win32' else [f'*{sys.version_info.major}{sys.version_info.minor}*.so', ],
    },
    ext_modules=extensions,
)
