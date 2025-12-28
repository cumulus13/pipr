#!/usr/bin/env python3
# File: pipr/pipr.py
# Author: Hadi Cahyadi <cumulus13@gmail.com>
# Date: 2025-11-30
# Description: Auto-install missing packages like 'go mod tidy' + detect imports from .py files
# License: MIT

import os
import sys
import traceback
import ast
import time
import json
if len(sys.argv) > 1 and any('--debug' == arg for arg in sys.argv):
    print("🐞 Debug mode enabled")
    os.environ["DEBUG"] = "1"
    os.environ['LOGGING'] = "1"
    os.environ.pop('NO_LOGGING', None)
    os.environ['TRACEBACK'] = "1"
    os.environ["LOGGING"] = "1"
else:
    os.environ['NO_LOGGING'] = "1"
try:
    from richcolorlog import setup_logging  # type: ignore
    logger = setup_logging(
        name="pipr",
        level="INFO",
        log_file_name="pipr.log",
        log_file=True,
        syslog=True,
        syslog_host="127.0.0.1",
        syslog_port=518,
        exceptions=['gntp']
    )
    HAS_RICHCOLORLOG=True
except:
    HAS_RICHCOLORLOG=False
    import logging

    try:
        from .custom_logging import get_logger  # type: ignore
    except ImportError:
        from custom_logging import get_logger  # type: ignore
    
    logging.getLogger('gntp').setLevel(logging.CRITICAL)

    logger = get_logger('notif-center', level=logging.INFO)


try:
    if HAS_RICHCOLORLOG:
        from richcolorlog import print_exception as tprint  # type: ignore
except:
    def tprint(*args, **kwargs):
        traceback.print_exc()

import platform
import re
import subprocess
import argparse
from pathlib import Path
from packaging import version
from packaging.specifiers import SpecifierSet
from importlib import metadata
try:
    import requests
    HAS_REQUESTS = True
except:
    HAS_REQUESTS = False
try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Confirm
    HAS_RICH = True
except:
    try:
        from make_colors import Console  # type: ignore
        from make_colors.table import Table  # type: ignore
        from make_colors import Confirm  # type: ignore
        HAS_MAKE_COLOR = False
    except:
        print("ERROR: please install `rich` or `make_colors` before !")
        sys.exit()

if HAS_RICH:  # type: ignore
    from rich import traceback as rtraceback
    rtraceback.install(show_locals=False, width=os.get_terminal_size()[0], theme='fruity', word_wrap=True)
else:
    try:
        from ctraceback import CTraceback
        sys.excepthook = CTraceback()
    except:
        pass

from gntp.notifier import GrowlNotifier
from licface import CustomRichHelpFormatter
from typing import Set, Optional, List, Tuple

from pypi_info import PyPIClient, PackageInfoDisplay  # type: ignore

REQ_FILE = "requirements.txt"
REQ_INSTALL_FILE = "requirements-install.txt"
console = Console()

# Growl notifier setup
growl = GrowlNotifier(
    applicationName="pipr",
    notifications=["Update", "Info", "Error"],
    defaultNotifications=["Update"]
)
growl.register()

# Standard library modules (Python 3.x) - should NOT be installed via pip
STDLIB_MODULES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
    'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
    'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
    'dis', 'distutils', 'doctest', 'dummy_threading', 'email', 'encodings', 'ensurepip',
    'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
    'formatter', 'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass',
    'gettext', 'glob', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http',
    'idlelib', 'imaplib', 'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress',
    'itertools', 'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging',
    'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder',
    'msilib', 'msvcrt', 'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers',
    'operator', 'optparse', 'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle',
    'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib', 'posix',
    'posixpath', 'pprint', 'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr',
    'pydoc', 'queue', 'quopri', 'random', 're', 'readline', 'reprlib', 'resource',
    'rlcompleter', 'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve',
    'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket',
    'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string',
    'stringprep', 'struct', 'subprocess', 'sunau', 'symbol', 'symtable', 'sys',
    'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios',
    'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize',
    'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types',
    'typing', 'typing_extensions', 'unicodedata', 'unittest', 'urllib', 'uu', 'uuid',
    'venv', 'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound',
    'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib',
    '_thread', '__future__', '__main__'
}

# Common package name mappings (import name -> pip package name)
PACKAGE_MAPPINGS = {
    'cv2': 'opencv-python',
    'PIL': 'Pillow',
    'Image': 'Pillow',
    'sklearn': 'scikit-learn',
    'yaml': 'pyyaml',
    'dotenv': 'python-dotenv',
    'dateutil': 'python-dateutil',
    'magic': 'python-magic',
    'bs4': 'beautifulsoup4',
    'cv': 'opencv-python',
    'OpenSSL': 'pyOpenSSL',
    'wx': 'wxPython',
}


def send_growl(title, message, priority=1, active = True):
    """Send notification via Growl."""
    if not active:
        return False
    try:
        growl.notify(
            noteType="Update",
            title=title,
            description=message,
            sticky=False,
            priority=priority
        )
        return True
    except Exception as e:
        console.print(f"[red]Growl error:[/red] {e}")
    return False

def get_pypi_info(package_name):
    """Get package info from PyPI JSON API with fallback to urllib."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    
    # Try using requests first
    if HAS_REQUESTS:
        try:
            response = requests.get(url, timeout=5)  # type: ignore
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch PyPI info for {package_name}: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Error fetching PyPI info for {package_name} using requests: {e}")
            # Don't return here, fallback to urllib
    else:
        console.print("\n[cyan]ℹ️  'requests' module not found, using urllib as fallback for PyPI checks.[/cyan]")

    
    # Fallback to urllib if requests is not available or failed
    try:
        import urllib.request
        import urllib.error
        
        logger.info(f"Using urllib as fallback to fetch PyPI info for {package_name}")
        
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'pipr/1.0'}
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                return json.loads(data)
            else:
                logger.warning(f"Failed to fetch PyPI info for {package_name}: {response.status}")
                return None
                
    except urllib.error.HTTPError as e:  # type: ignore
        logger.warning(f"HTTP Error fetching PyPI info for {package_name}: {e.code} - {e.reason}")
        return None
    except urllib.error.URLError as e:  # type: ignore
        logger.warning(f"URL Error fetching PyPI info for {package_name}: {e.reason}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching PyPI info for {package_name} using urllib: {e}")
        return None

def get_python_version_requirement(pypi_data):
    """Extract Python version requirement from PyPI data."""
    if not pypi_data:
        return None
    
    try:
        requires_python = pypi_data.get('info', {}).get('requires_python')
        return requires_python
    except Exception as e:
        logger.warning(f"Error extracting Python version: {e}")
        return None


def check_python_version_compatibility(package_name, requires_python):
    """Check if current Python version is compatible with package requirements from PyPI."""
    if not requires_python:
        return True, None
    
    current_version = version.parse(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    try:
        spec_set = SpecifierSet(requires_python)
        
        # Check apakah current Python version MASUK dalam requirement dari PyPI
        if current_version in spec_set:
            return True, None
        else:
            # TIDAK COCOK - current Python tidak memenuhi requirement dari PyPI
            return False, f"Package '{package_name}' requires Python {requires_python}, but current system has Python {current_version}"
    except Exception as e:
        logger.warning(f"Error checking Python version compatibility: {e}")
        return True, None

def get_venv_base_path():
    """Get base path for virtual environments based on platform."""
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: try c:\VENV -> %HOME%\.pip\VENV -> %APPDATA%\.pipr\VENV
        paths = [
            Path("c:/VENV"),
            Path.home() / ".pip" / "VENV",
            Path(os.getenv('APPDATA', Path.home() / "AppData" / "Roaming")) / ".pipr" / "VENV"
        ]
    else:
        # Linux/Mac: try ~/.venv -> ~/.pip/VENV -> ~/.local/share/pipr/VENV
        paths = [
            Path.home() / ".venv",
            Path.home() / ".pip" / "VENV",
            Path.home() / ".local" / "share" / "pipr" / "VENV"
        ]
    
    # Check which path exists or can be created
    for path in paths[:-1]:
        if path.exists():
            return path
    
    # Last option: create the directory
    last_path = paths[-1]
    last_path.mkdir(parents=True, exist_ok=True)
    return last_path


def get_project_name():
    """Get project name from setup.py, pyproject.toml, or parent folder."""
    # Try setup.py first
    setup_py = Path.cwd() / "setup.py"
    if setup_py.exists():
        try:
            with open(setup_py, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    is_setup = (isinstance(func, ast.Name) and func.id == 'setup') or \
                               (isinstance(func, ast.Attribute) and func.attr == 'setup')
                    if is_setup:
                        for kw in node.keywords:
                            if kw.arg == 'name':
                                if isinstance(kw.value, ast.Constant):
                                    return kw.value.value
                                elif hasattr(kw.value, 's'):
                                    return kw.value.s
        except Exception as e:
            logger.warning(f"Could not parse setup.py for name: {e}")
    
    # Try pyproject.toml
    pyproject = Path.cwd() / "pyproject.toml"
    if pyproject.exists() and _has_toml_support():
        try:
            if sys.version_info >= (3, 11):
                import tomllib as toml
                with open(pyproject, 'rb') as f:
                    data = toml.load(f)
            else:
                try:
                    import toml
                except ImportError:
                    import tomli as toml
                with open(pyproject, 'r', encoding='utf-8') as f:
                    data = toml.load(f)
            
            if 'project' in data and 'name' in data['project']:
                return data['project']['name']
            elif 'tool' in data and 'poetry' in data['tool'] and 'name' in data['tool']['poetry']:
                return data['tool']['poetry']['name']
        except Exception as e:
            logger.warning(f"Could not parse pyproject.toml for name: {e}")
    
    # Fallback to parent folder name
    return Path.cwd().name


def create_virtualenv(venv_name, reqs):
    """Create virtual environment and install packages."""
    venv_base = get_venv_base_path()
    venv_path = venv_base / venv_name
    
    console.print(f"\n[yellow]⚠️  Version conflicts detected. Creating virtual environment...[/yellow]")
    console.print(f"[cyan]Virtual environment will be created at:[/cyan] {venv_path}")
    time.sleep(2)
    
    try:
        # Create virtual environment
        console.print(f"[cyan]Creating virtual environment '{venv_name}'...[/cyan]")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
        
        # Determine pip path based on platform
        if platform.system().lower() == "windows":
            pip_path = venv_path / "Scripts" / "pip.exe"
            python_path = venv_path / "Scripts" / "python.exe"
        else:
            pip_path = venv_path / "bin" / "pip"
            python_path = venv_path / "bin" / "python"
        
        # Upgrade pip in venv
        console.print(f"[cyan]Upgrading pip in virtual environment...[/cyan]")
        subprocess.check_call([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install packages
        console.print(f"[cyan]Installing packages in virtual environment...[/cyan]")
        for pkg, spec in reqs:
            pkg_spec = f"{pkg}{spec or ''}"
            console.print(f"  • Installing {pkg_spec}")
            subprocess.check_call([str(pip_path), "install", pkg_spec])
        
        console.print(f"\n[green]✓ Virtual environment '{venv_name}' created successfully![/green]")
        console.print(f"[cyan]Location:[/cyan] {venv_path}")
        console.print(f"\n[bold yellow]To activate the virtual environment:[/bold yellow]")
        
        if platform.system().lower() == "windows":
            console.print(f"  {venv_path}\\Scripts\\activate")
        else:
            console.print(f"  source {venv_path}/bin/activate")
        
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Failed to create virtual environment:[/red] {e}")
        if str(os.getenv('TRACEBACK', '0').lower()) in ['1', 'yes', 'true']:
            tprint(*sys.exc_info(), None, False, True)
        return False


def parse_requirements(file_path):
    """Parse requirements.txt into a list of (package, specifier)."""
    reqs = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Handle conditional markers like sys_platform == "win32"
            if ";" in line:
                pkg, cond = map(str.strip, line.split(";", 1))
                if "sys_platform" in cond:
                    sys_name = platform.system().lower()
                    if "win32" in cond and sys_name != "windows":
                        continue
                    if "linux" in cond and sys_name != "linux":
                        continue
                line = pkg

            match = re.match(r"([A-Za-z0-9_.-]+)(.*)", line)
            logger.alert(f"match: {match}")
            if match:
                name, spec = match.groups()
                logger.info(f"name: {name}")
                spec = spec.strip()
                logger.info(f"spec: {spec}")
                reqs.append((name, spec if spec else None))
    return reqs


def extract_imports_from_file(file_path: Path) -> Set[str]:
    """Extract all imported modules from a Python file using AST."""
    imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            # Handle "import module" or "import module as alias"
            if isinstance(node, ast.Import):
                for name in node.names:
                    module = name.name.split('.')[0]  # Get base module
                    imports.add(module)
                    logger.info(f"Found import: {module}")
            
            # Handle "from module import something"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]  # Get base module
                    imports.add(module)
                    logger.info(f"Found from import: {module}")
        
        logger.notice(f"Extracted {len(imports)} imports from {file_path}")
        
    except Exception as e:
        console.print(f"[yellow]Warning: [1] Could not parse {file_path}:[/] {e}")
        if str(os.getenv('TRACEBACK', '0').lower()) in ['1', 'yes', 'true']:
            tprint(*sys.exc_info(), None, False, True)
    
    return imports


def extract_imports_from_directory(directory: Path, recursive: bool = True) -> Set[str]:
    """Extract all imports from all .py files in a directory."""
    all_imports = set()
    
    if recursive:
        py_files = list(directory.rglob("*.py"))
    else:
        py_files = list(directory.glob("*.py"))
    
    console.print(f"[cyan]Scanning {len(py_files)} Python files for imports...[/cyan]")
    
    for py_file in py_files:
        imports = extract_imports_from_file(py_file)
        all_imports.update(imports)
    
    return all_imports


def filter_third_party_packages(imports: Set[str]) -> Set[str]:
    """Filter out standard library modules and return only third-party packages."""
    third_party = set()
    
    for module in imports:
        # Skip if it's a standard library module
        if module in STDLIB_MODULES:
            logger.info(f"Skipping stdlib module: {module}")
            continue
        
        # Map import name to pip package name if needed
        package_name = PACKAGE_MAPPINGS.get(module, module)
        
        # Check if package is installed
        try:
            metadata.version(package_name)
            third_party.add(package_name)
            logger.info(f"Found installed third-party: {package_name}")
        except metadata.PackageNotFoundError:
            # Not installed, but might be a third-party package
            third_party.add(package_name)
            logger.warning(f"Found uninstalled third-party: {package_name}")
    
    return third_party


def parse_python_file(file_path: Path) -> List[Tuple[str, Optional[str]]]:
    """Parse a Python file and return list of (package, None) tuples."""
    imports = extract_imports_from_file(file_path)
    third_party = filter_third_party_packages(imports)
    
    # Convert to list of tuples (package, None) - no version specified
    reqs = [(pkg, None) for pkg in sorted(third_party)]
    
    if reqs:
        console.print(f"[bold green]✓ Parsed {file_path}:[/] [bold cyan]{len(reqs)} third-party packages[/]")
    
    return reqs  # type: ignore


def parse_python_directory(directory: Path, recursive: bool = True) -> List[Tuple[str, Optional[str]]]:
    """Parse all Python files in a directory and return requirements."""
    imports = extract_imports_from_directory(directory, recursive)
    third_party = filter_third_party_packages(imports)
    
    # Convert to list of tuples (package, None) - no version specified
    reqs = [(pkg, None) for pkg in sorted(third_party)]
    
    if reqs:
        console.print(f"[bold green]✓ Parsed directory {directory}:[/] [bold cyan]{len(reqs)} unique third-party packages[/]")
    
    return reqs  # type: ignore


def run_pip_install_from_file(file_path, force_retry=False):
    """Run pip install from requirements-install.txt file."""
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(file_path)]
    console.print(f"[green]>>> Running:[/green] {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        send_growl("Install Success", f"Installed from {file_path}")
        # remove file if install succeeded
        Path(file_path).unlink(missing_ok=True)
        console.print(f"[green]Removed {file_path} after successful install[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Install error:[/red] {e}")
        send_growl("Install Error", f"Failed from {file_path}", priority=2)

        if force_retry:
            console.print("[yellow]Retrying installation (force mode)...[/yellow]")
            return run_pip_install_from_file(file_path, force_retry=False)

        if Confirm.ask("Retry installation?"):
            return run_pip_install_from_file(file_path, force_retry=False)

        return False


def run_pip_install(packages, force_retry=False, auto_mode=False):
    """Run pip install for a list of packages, saving them to requirements-install.txt."""
    # Save to requirements-install.txt
    with open(REQ_INSTALL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(packages))

    return run_pip_install_from_file(REQ_INSTALL_FILE, force_retry=force_retry)

def miss_conflict_check(pkg, spec):
    version_conflicts = []
    missing_packages = []
    
    # Check if package is installed
    try:
        inst_ver = metadata.version(pkg)
    except metadata.PackageNotFoundError:
        inst_ver = None
    
    # Check for version conflicts
    if inst_ver is not None and spec:
        iv = version.parse(inst_ver)
        spec_set = SpecifierSet(spec)
        
        if iv not in spec_set:
            version_conflicts.append((pkg, inst_ver, spec))
    elif inst_ver is None:
        missing_packages.append((pkg, spec))

    return version_conflicts, missing_packages

def check_packages(reqs, force_retry=False, force_install=False, summary_only=False, show=True, auto_mode=True, send_notification=True): #, package_name = None):
    """Check installed packages vs requirements and collect installs if needed.
    
    Args:
        auto_mode: Now defaults to True - auto-install if no conflicts detected
    """
    logger.warning(f"reqs: {reqs}")
    
    # Check PyPI for Python version requirements and detect conflicts
    python_conflicts = []
    version_conflicts = []
    missing_packages = []

    # if package_name and isinstance(package_name, (list or tuple)):
    #     version_conflicts, missing_packages = miss_conflict_check(package_name[0], package_name[1])

    with console.status("[cyan]🔎 Checking PyPI for package information ...[/cyan]", spinner='point'):
    
        for pkg, spec in reqs:
            # Get PyPI info
            pypi_data = get_pypi_info(pkg)
            logger.debug(f"pypi_data: {pypi_data}")
            
            # Check Python version compatibility
            if pypi_data:
                requires_python = get_python_version_requirement(pypi_data)
                logger.debug(f"requires_python: {requires_python}")
                if requires_python:
                    logger.debug(f"requires_python: {requires_python}")
                    is_compatible, error_msg = check_python_version_compatibility(pkg, requires_python)
                    if not is_compatible:
                        python_conflicts.append(error_msg)
            
            # Check if package is installed
            version_conflicts, missing_packages = miss_conflict_check(pkg, spec)
            # try:
            #     inst_ver = metadata.version(pkg)
            # except metadata.PackageNotFoundError:
            #     inst_ver = None
            
            # # Check for version conflicts
            # if inst_ver is not None and spec:
            #     iv = version.parse(inst_ver)
            #     spec_set = SpecifierSet(spec)
                
            #     if iv not in spec_set:
            #         version_conflicts.append((pkg, inst_ver, spec))
            # elif inst_ver is None:
            #     missing_packages.append((pkg, spec))
        
    # If there are Python version conflicts, abort
    if python_conflicts:
        console.print("\n[bold red]✗ Python Version Conflicts Detected:[/bold red]")
        for conflict in python_conflicts:
            console.print(f"  • [red]{conflict}[/red]")
        console.print("\n[yellow]Please upgrade your Python version or adjust your requirements.[/yellow]")
        if __name__ == '__main__':
            sys.exit(1)
    
    # If there are version conflicts, use virtual environment
    if version_conflicts and not force_install and auto_mode:
        console.print("\n[bold yellow]⚠️  Package Version Conflicts Detected:[/bold yellow]")
        for pkg, installed, required in version_conflicts:
            console.print(f"  • {pkg}: installed={installed}, required={required}")
        
        # Get project name for venv
        project_name = get_project_name()
        venv_name = f"{project_name}-env"
        
        # Create virtual environment with all requirements
        create_virtualenv(venv_name, reqs)

        return reqs, [], python_conflicts, version_conflicts, missing_packages
    
    # No conflicts detected - proceed with normal installation (auto mode)
    if force_install:
        for pkg, spec in reqs:
            cmd = [sys.executable, "-m", "pip", "install", f"{pkg}{spec or ''}"]
            print(f"{' '.join(cmd)}")
            try:
                subprocess.check_call(cmd)
            except Exception as e:
                if force_retry:
                    console.print(f"[yellow]Retrying installation (force mode)...[/yellow]")
                    while 1:
                        try:
                            subprocess.check_call(cmd)
                            break
                        except Exception as e:
                            console.print(f"[red]✗ Install error:[/red] {e}")
                            send_growl("Install Error", f"Failed to install {pkg}", priority=2, active=send_notification)
        return reqs, [], python_conflicts, version_conflicts, missing_packages

    if show:
        table = Table(title="Package Version Checker", header_style="bold #FFAA7F")
        table.add_column("Package", style="bold")
        table.add_column("Installed", style="bold #00FFFF")
        table.add_column("Required", style="bold #AA55FF")
        table.add_column("PyPI Latest", style="bold #FFFF00")
        table.add_column("", style="bold")  # emoji column
        table.add_column("Status")

    to_install = []  # collect install/upgrade/downgrade tasks

    for pkg, spec in reqs:
        try:
            inst_ver = metadata.version(pkg)
        except metadata.PackageNotFoundError as e:
            logger.error(e)
            inst_ver = None

        # Get PyPI info
        pypi_data = get_pypi_info(pkg)
        pypi_latest = pypi_data.get('info', {}).get('version', '-') if pypi_data else '-'

        status = ""
        emoji = ""

        logger.warning(f"inst_ver: {inst_ver}")

        if inst_ver is None:
            # Package not installed - auto-install in auto_mode (now default)
            status = "[bold red]Not Installed[/]"
            emoji = "🚫"
            if not summary_only:
                send_growl(f"{pkg} Missing", f"{pkg} is not installed.", active=send_notification)
            
            if auto_mode:
                # Auto-install missing packages without asking
                to_install.append(f"{pkg}{spec or ''}")
                status = "[bold #FFFF00]Will auto-install[/]"
                emoji = "⚡"
            else:
                to_install.append(f"{pkg}{spec or ''}")
            
            if show:
                table.add_row(pkg, "", spec or "-", pypi_latest, emoji, status)  # type: ignore
            continue

        iv = version.parse(inst_ver)
        if spec:
            spec_set = SpecifierSet(spec)

            if "==" in spec:  # exact match required
                req_ver = spec.split("==")[1]
                if iv == version.parse(req_ver):
                    emoji = "✅"
                    status = "[bold #AAAAFF]Exact match[/]"
                    if not summary_only:
                        send_growl(f"{pkg} OK", f"{pkg} {inst_ver} matches {spec}", active=send_notification)
                else:
                    emoji = "⚠ "
                    status = f"[bold #FFFF00]Mismatch (need {spec})[/]"
                    if not summary_only:
                        send_growl(f"{pkg} Mismatch", f"{pkg} {inst_ver} != required {spec}", active=send_notification)
            else:
                if iv in spec_set:
                    emoji = "✅"
                    status = f"[bold #AAAAFF]OK (within {spec})[/]"
                    if not summary_only:
                        send_growl(f"{pkg} OK", f"{pkg} {inst_ver} satisfies {spec}", active=send_notification)
                else:
                    emoji = "⚠ "
                    status = f"[bold #FFFF00]Not in range {spec}[/]"
                    if not summary_only:
                        send_growl(f"{pkg} Out of range", f"{pkg} {inst_ver} not in {spec}", active=send_notification)
        else:
            emoji = "✅"
            status = "[bold #0055FF]No version rule[/]"
            if not summary_only:
                send_growl(f"{pkg} Checked", f"{pkg} {inst_ver}", active=send_notification)

        if show:
            table.add_row(pkg, inst_ver or "-", spec or "-", pypi_latest, emoji, status)  # type: ignore

    if show:
        console.print(table)  # type: ignore

    if summary_only:
        # Do not install anything in summary mode
        return reqs, to_install, python_conflicts, version_conflicts, missing_packages

    # Auto-install missing packages (default behavior)
    if to_install and auto_mode:
        console.print(f"\n[green]📦 Auto-installing {len(to_install)} package(s):[/]")
        for pkg in to_install:
            console.print(f"  • {pkg}")
        success = run_pip_install(to_install, force_retry=force_retry, auto_mode=True)
        if success:
            console.print(f"[green]✅ Successfully installed {len(to_install)} package(s)[/]")
        else:
            console.print("[bold red]❌ Some packages failed to install.[/]")

    logger.notice(f"to_install: {to_install}")
    if not to_install:
        console.print("\n✅ [bold #FFAAFF]All requirements satisfied. Nothing to install.[/]")

    return reqs, to_install, python_conflicts, version_conflicts, missing_packages

def _has_toml_support() -> bool:
    """Check if toml/tomli is available without importing them globally."""
    if sys.version_info >= (3, 11):
        return True  # tomllib is built-in
    try:
        __import__('toml')
        return True
    except ImportError:
        try:
            __import__('tomli')
            return True
        except ImportError:
            return False

def _extract_package_name(dep_string: str) -> Optional[str]:
    dep = dep_string.split('[')[0].split('[')[0].split(';')[0].strip()
    for op in ['>=', '<=', '==', '!=', '~=', '>', '<']:
        dep = dep.split(op)[0]
    return dep.lower() if dep else None

def _extract_from_list_node(node) -> Set[str]:
    deps = set()
    if isinstance(node, ast.List):
        for elt in node.elts:
            val = elt.value if isinstance(elt, ast.Constant) else \
                  elt.s if hasattr(elt, 's') else None  # type: ignore
            if val:
                logger.notice(f"val: {val}")
                deps.add(val)
    return deps

def convert_spec(spec: str):
    """
    Convert Poetry-style version constraints into PEP 440 (setup.py compatible).
    Supports:
        ^ caret
        ~ tilde
        >= <= < > ==
        *
        exact
        ranges
        comma-separated
        union (|)
    """
    spec = spec.strip()

    # ---------------------------
    # 1. UNION ("|")
    # ---------------------------
    if "|" in spec:
        parts = [convert_spec(x) for x in spec.split("|")]
        return " | ".join(parts)

    # ---------------------------
    # 2. Comma separated
    # ---------------------------
    if "," in spec:
        parts = [convert_spec(x) for x in spec.split(",")]
        return ",".join(parts)

    # ---------------------------
    # 3. CARET ^X.Y.Z
    # ---------------------------
    if spec.startswith("^"):
        version = spec[1:].strip()
        return convert_caret(version)

    # ---------------------------
    # 4. TILDE ~X.Y.Z
    # ---------------------------
    if spec.startswith("~"):
        version = spec[1:].strip()
        return convert_tilde(version)

    # ---------------------------
    # 5. WILDCARD "1.*"
    # ---------------------------
    if "*" in spec:
        return convert_wildcard(spec)

    # ---------------------------
    # 6. RANGE OPERATORS
    # ---------------------------
    if re.match(r"^(>=|<=|<|>|==)", spec):
        return spec.replace(" ", "")

    # ---------------------------
    # 7. EXACT version
    # ---------------------------
    if re.match(r"^\d+(\.\d+)*$", spec):
        return f"=={spec}"

    print(f"WARNING: Unsupported spec: {spec}")
    return ""


# ---------------------------
# CARET
# ---------------------------
def convert_caret(version: str):
    parts = version.split(".")
    parts += ["0"] * (3 - len(parts))
    major, minor, patch = map(int, parts)

    if major > 0:
        upper = f"{major + 1}.0.0"
    elif minor > 0:
        upper = f"0.{minor + 1}.0"
    else:
        upper = f"0.0.{patch + 1}"

    return f">={version},<{upper}"


# ---------------------------
# TILDE
# ---------------------------
def convert_tilde(version: str):
    parts = version.split(".")
    parts += ["0"] * (3 - len(parts))
    major, minor, patch = map(int, parts)

    upper = f"{major}.{minor + 1}.0"
    return f">={version},<{upper}"


# ---------------------------
# WILDCARD
# ---------------------------
def convert_wildcard(spec: str):
    # "1.*" → >=1.0,<2.0
    parts = spec.split(".")
    major = int(parts[0])

    if len(parts) == 2 and parts[1] == "*":
        return f">={major}.0,<{major+1}.0"

    # "1.2.*" → >=1.2.0,<1.3.0
    if len(parts) == 3 and parts[2] == "*":
        minor = int(parts[1])
        return f">={major}.{minor}.0,<{major}.{minor+1}.0"

    print(f"WARNING: Unsupported wildcard: {spec}")
    return ""

def parse_deps(deps):
    reqs = []
    for line in deps:
        match = re.match(r"([A-Za-z0-9_.-]+)(.*)", line)
        logger.alert(f"match: {match}")
        if match:
            name, spec = match.groups()
            logger.info(f"name: {name}")
            spec = spec.strip()
            logger.info(f"spec: {spec}")
            reqs.append((name, spec if spec else None))
    return reqs

def parse_pyproject_toml(pyproject_path = None) -> List[str]:
    deps = set()
    pyproject_path = pyproject_path or Path.cwd() / 'pyproject.toml'
    if not pyproject_path.exists():
        return []

    if not _has_toml_support():
        console.print("[bold yellow]Warning: toml/tomli not installed, cannot parse pyproject.toml[/]")
        console.print("[bold cyan]Install with:[/] pip install toml  [bold yellow]or[/] pip install tomli")
        logger.notice(f"deps: {deps}")
        return []

    try:
        if sys.version_info >= (3, 11):
            import tomllib as toml
            with open(pyproject_path, 'rb') as f:
                data = toml.load(f)
        else:
            try:
                import toml
            except ImportError:
                import tomli as toml
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)

        if 'project' in data and 'dependencies' in data['project']:
            for dep in data['project']['dependencies']:
                logger.warning(f"dep: {dep}")
                deps.add(dep)
        if 'tool' in data and 'poetry' in data['tool']:
            poetry = data['tool']['poetry']
            logger.warning(f"poetry: {poetry}")
            for key in ['dependencies']:
                if key in poetry:
                    for dep, ver in poetry[key].items():
                        if isinstance(ver, dict):
                            ver = ver.get('version')
                        logger.alert(f"dep: {dep}")
                        logger.alert(f"ver: {ver}")
                        spec = convert_spec(ver)  # type: ignore
                        logger.alert(f"spec: {spec}")
                        if dep != 'python':
                            deps.add(f"{dep}{spec}")
        console.print(f"[bold green]✓ Parsed pyproject.toml:[/] [bold cyan]{len(deps)} dependencies[/]")
    except Exception as e:
        console.print(f"[bold red]Error parsing pyproject.toml:[/] {e}")
    logger.notice(f"deps: {deps}")
    deps = parse_deps(deps)
    logger.notice(f"deps: {deps}")
    return deps

def parse_setup_py(path = None) -> Set[str]:
    deps = set()
    path = path or Path.cwd() / 'setup.py'
    if not Path(path).exists():
        logger.notice(f"deps: {deps}")
        return deps
    try:
        with open(path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_setup = (isinstance(func, ast.Name) and func.id == 'setup') or \
                           (isinstance(func, ast.Attribute) and func.attr == 'setup')
                if is_setup:
                    for kw in node.keywords:
                        if kw.arg == 'install_requires':
                            logger.emergency(f"kw.value: {kw.value}")
                            deps.update(_extract_from_list_node(kw.value))

        logger.critical(f"deps: {deps}")
        if deps:
            deps = parse_deps(deps)
            logger.notice(f"deps: {deps}")
            console.print(f"[bold green]✓ Parsed setup.py:[/] [bold cyan]{len(deps)} dependencies[/]")
    except Exception as e:
        console.print(f"[bold yellow]Warning: [0] Could not parse setup.py:[/] {e}")
        if str(os.getenv('TRACEBACK', '0').lower()) in ['1', 'yes', 'true']:
            tprint(*sys.exc_info(), None, False, True)
    logger.notice(f"deps: {deps}")
    return deps  # type: ignore

def get_requirements_from_pypi(package):
    try:
        client = PyPIClient()
        display = PackageInfoDisplay()

        package_data = client.get_package_info(package)
        info = package_data.get('info', [])
        requires_dist = info.get('requires_dist', [])
        logger.debug(f"requires_dist: {requires_dist}")
        requires_python = info.get('requires_python', None)
        logger.debug(f"requires_python: {requires_python}")
        if not requires_dist and not requires_python:
            return []

        deps = display._parse_dependencies(requires_dist)
        logger.debug(f"deps: {deps}")
        if deps and deps.get('core'):
            data = [(i['name'], i.get('version') if i.get('version') != 'any' else '') for i in deps.get('core')]
            return data
        # return deps if deps else []

    except Exception as e:
        tprint(e)

    return []

def main():
    global REQ_FILE
    parser = argparse.ArgumentParser(
        description="Package requirements checker (like 'go mod tidy') + auto-detect imports from .py files", 
        formatter_class=CustomRichHelpFormatter, 
        prog='pipr'
    )

    parser.add_argument('FILE', nargs='?', help="requirements file or Python file/directory to scan (requirements.txt, requirements-install.txt, setup.py, pypproject.toml or any file) if not provided then default is auto search based from requirements.txt -> requirements-install.txt -> setup.py -> pypproject.toml, if none of thems a file then default as PACKAGE_NAME", metavar="FILE/PACKAGE_NAME but if a DIRECTORY then it will be search/scan any python file from not builtin import modules")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Scan Python files recursively in directory (used with --scan)")
    parser.add_argument("-f", "--force-retry", action="store_true",
                        help="Force retry installation automatically if error occurs")
    parser.add_argument("-F", '--force-install', action="store_true",
                        help="Force install packages without asking for confirmation")
    parser.add_argument("-s", "--summary", action="store_true",
                        help="Show summary table only (non-interactive, no install)")
    parser.add_argument("-c", "--check", action="store_true",
                        help="Same as '-s': show summary table only (non-interactive, no install)")
    parser.add_argument('-i', "--pypi", action="store", 
                        help = "Compare package direct to package on pypi.org")
    # parser.add_argument('-I', "--install", action="store_true", 
                        # help = "Install if no config. same as '-F' but checking before")
    parser.add_argument('-n', "--no-install", action="store_true", 
                        help = "Don't auto install")
    parser.add_argument('-z', "--no-show", action="store_true", 
                        help = "Don't show table and force no table")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Debugging process (logging)")

    args = parser.parse_args()

    if args.debug:
        try:
            os.environ.pop('NO_LOGGING')
        except:
            pass
        os.environ.update({'LOGGING':'1'})

    requirements = []
    is_python_file = False
    is_directory = False
    is_pypi_package = False

    # Check if FILE argument is provided and what type it is
    if args.FILE:
        logger.debug("processing args.FILE ...")
        file_path = Path(args.FILE)
        
        if file_path.is_file():
            if file_path.suffix == '.py':
                # It's a Python file - scan for imports
                is_python_file = True
                # console.print(f"[bold #00FFFF]🔍 Scanning Python file for imports:[/] {file_path}")
                with console.status(f"[bold #00FFFF]🔍 Scanning Python file for imports:[/] {file_path}", spinner='dots2'):
                    requirements = parse_python_file(file_path)
            elif file_path.name.startswith('require') and file_path.suffix == '.txt':
                # It's a requirements file
                REQ_FILE = args.FILE
                requirements = parse_requirements(REQ_FILE)
            elif file_path.name == 'setup.py':
                # It's setup.py
                requirements = parse_setup_py(file_path)
            elif file_path.name == 'pyproject.toml':
                # It's pyproject.toml
                requirements = parse_pyproject_toml(file_path)
            else:
                console.print(f"[yellow]⚠️  Unknown file type, trying to parse as requirements.txt...[/yellow]")
                REQ_FILE = args.FILE
                requirements = parse_requirements(REQ_FILE)
        
        elif file_path.is_dir():
            # It's a directory - scan all Python files
            is_directory = True
            # console.print(f"[bold #00FFFF]🔍 Scanning directory for Python imports:[/] {file_path}")
            with console.status(f"[bold #00FFFF]🔍 Scanning directory for Python imports:[/] {file_path}", spinner='dots2'):
                requirements = parse_python_directory(file_path, recursive=args.recursive)
        
        else:
            with console.status(f"🔎 [bold #577F00]trying search package on pypi.org for [/] [bold #FFFF00]`{args.FILE}`[/] [bold #577F00]...[/]", spinner='point'):
                logger.debug(f"🔎 trying search package on pypi.org for `{args.FILE}` ...")
                requirements = get_requirements_from_pypi(args.FILE)
                is_pypi_package = True
                if requirements:
                    console.print(f"✅ [bold #FFFF00]found requirements on pypi.org for[/] [bold #00FFFF]`{args.FILE}`[/] [bold #FFFF00]...[/]")
                    logger.debug(f"requirements: {requirements}")
            if not is_pypi_package or not requirements:
                console.print(f"\n:cross_mark: [red]File or directory not found:[/red] {args.FILE}\n")
                parser.print_help()
                sys.exit(1)

    elif args.pypi and not args.FILE:
        logger.debug("processing args.pypi ...")
        print("\n")
        # with console.status(f"🔎 [bold #577F00]trying find package on pypi.org for [/] [bold #FFFF00]`{args.pypi}`[/] [bold #577F00]...[/], [bold #FFAA00]if no conflicts this will be auto Auto-installing  ", spinner='point'):
        console.print(f"🔎 [bold #577F00]trying find package on pypi.org for [/] [bold #FFFF00]`{args.pypi}`[/] [bold #577F00]...[/] {'[bold #FFAA00]if no conflicts this will be auto Auto-installing' if not args.no_install else '[bold #FF5500]No-Auto-Install'}  [/]")
        requirements = get_requirements_from_pypi(args.pypi)
        if requirements:
            console.print(f"✅ [bold #FFFF00]found requirements on pypi.org for[/] [bold #00FFFF]`{args.pypi}`[/] [bold #FFFF00]...[/]")
        logger.debug(f"requirements: {requirements}")
        # print("\n")
    else:
        logger.debug("processing alternative (else) ...")
        # No FILE argument - check for standard requirement files
        requirement_files = [
            Path.cwd() / 'setup.py',
            Path.cwd() / 'pyproject.toml',
            Path.cwd() / REQ_FILE,
            Path.cwd() / REQ_INSTALL_FILE,
        ]

        REQ_FOUND = []

        for i in requirement_files:
            if Path(i).exists() and Path(i).stat().st_size > 0:
                REQ_FOUND.append(Path(i))

        # If requirements-install.txt exists and is not empty -> install directly
        if Path(REQ_INSTALL_FILE) in REQ_FOUND:
            console.print(f"[bold #FFFF00]Found {REQ_INSTALL_FILE}, installing directly...[/]")
            run_pip_install_from_file(REQ_INSTALL_FILE, force_retry=args.force_retry)
            sys.exit(0)

        if not REQ_FOUND:
            # No standard requirement files found, scan current directory for Python files
            console.print(f"[yellow]⚠️  No standard requirement files found.[/yellow]")
            # console.print(f"[cyan]🔍 Scanning current directory for Python imports...[/cyan]")
            is_directory = True
            with console.status(f"[bold #00FFFF]🔍 Scanning current directory for Python imports...[/]", spinner='point'):
                requirements = parse_python_directory(Path.cwd(), recursive=args.recursive)
            
            if len(requirements) < 1:
                console.print(f"\n:cross_mark: [red]No Python files found or no imports detected![/red]\n")
                parser.print_help()
                sys.exit(1)
        else:
            # Try to parse standard requirement files in order
            requirements = parse_setup_py()
            logger.warning(f"requirements: {requirements}")
            
            if len(requirements) < 1:
                console.print(f"\n:cross_mark: [#FFFF00]'setup.py' has no requirements or no file ![/]")
                # console.print(f"\n🚀 [#00FFFF]try to get from 'pyproject.toml' ...[/]")
                with console.status(f"\n🚀 [#00FFFF]try to get from 'pyproject.toml' ...[/]", spinner='growVertical'):
                    requirements = parse_pyproject_toml()
                    logger.warning(f"requirements: {requirements}")
                
                if len(requirements) < 1:
                    console.print(f"\n:cross_mark: [#FFFF00]'pyproject.toml' has no requirements or no file ![/]")
    
    logger.emergency(f"requirements: {requirements}")
    
    # If still no requirements found, try requirements.txt
    if len(requirements) < 1 and not is_python_file and not is_directory:
        if not args.pypi and not Path(REQ_FILE).exists():
            console.print(f"\n❌ [red bold]File {REQ_FILE} not found![/]\n")
            parser.print_help()
            sys.exit(1)
        if not args.pypi:
            logger.notice(f"REQ_FILE: {REQ_FILE}")
            requirements = parse_requirements(REQ_FILE)
            logger.warning(f"requirements: {requirements}")
        
        if len(requirements) < 1 and not args.pypi:
            console.print(f"\n❌ [#FFFF00]requirements.txt is empty ![/]")
            sys.exit(1)

    
    # Show mode info
    if is_python_file:
        console.print(f"[bold cyan]📄 Detected Python file mode[/]")
    elif is_directory:
        console.print(f"[bold cyan]📁 Detected directory scan mode {'(recursive)' if args.recursive else '(non-recursive)'}[/]")

    # Check and install packages (auto mode is now default)
    reqs, to_install, python_conflicts, version_conflicts, missing_packages = check_packages(
        requirements,
        force_retry=args.force_retry,
        force_install=args.force_install,
        summary_only=args.summary or args.check,
        show=True if args.summary or args.check else True if not args.no_show else False,
        auto_mode=True if not args.no_install else False  # Always True now (default behavior)
    )

    logger.debug(f"reqs: {reqs}")
    logger.debug(f"args.force_retry: {args.force_retry}")
    logger.debug(f"args.force_install: {args.force_install}")
    logger.debug(f"args.summary: {args.summary}")
    logger.debug(f"args.check: {args.check}")
    logger.debug(f"args.no_show: {args.no_show}")
    logger.debug(f"args.no_install: {args.no_install}")

    logger.debug(f"to_install: {to_install}")
    logger.debug(f"python_conflicts: {python_conflicts}")
    logger.debug(f"version_conflicts: {version_conflicts}")
    logger.debug(f"missing_packages: {missing_packages}")

    # if args.install and (not version_conflicts or not python_conflicts) and args.pypi:
    if (not version_conflicts or not python_conflicts) and args.pypi:
        if not to_install and not args.no_install:
            return True
        if args.no_install: return True
        # console.print(f"🚩 [bold #FFAA00]start[/] [bold #AA55FF]install package[/] [bold #00FFFF]`{args.pypi}`[/] ...")
        with console.status(f"🚩 [bold #FFAA00]start[/] [bold #AA55FF]install package[/] [bold #00FFFF]`{args.pypi}`[/] ...", spinner="material") as status:
            p = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', args.pypi],
                # capture_output=True, # To capture stdout and stderr
                # text=True,           # To decode stdout/stderr as string (text)
                check=False,          # Set to False to not raise CalledProcessError
                stdout=subprocess.PIPE if not args.debug else None,
                stderr=subprocess.PIPE if not args.debug else None,

            )
            if p.returncode == 0:
                # console.print(p.stdout)
                status.update(f"✅ [bold #00FFFF]install package[/] [bold #00FFFF]`{args.pypi}`[/] [bold #00FFFF]successfully.[/]")
            elif p.returncode != 0:
                # console.print(p.stderr)
                # console.print(p.stdout)
                status.update(f"❌ [bold red]install package[/] [bold #FFFF00]`{args.pypi}`[/] [bold red blink]failed !.[/]")


if __name__ == "__main__":
    main()