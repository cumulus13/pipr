#!/usr/bin/env python
#author: Hadi Cahyadi <cumulus13@gmail.com>
#license: MIT

import os
import sys
import traceback
import ast
try:
    from ctraceback import print_traceback as tprint
except:
    def tprint(*args, **kwargs):
        traceback.print_exc()
os.environ.update({'NO_LOGGING':'1'})
try:
    os.environ.pop('LOGGING')
except:
    pass
from richcolorlog import setup_logging
logger = setup_logging(exceptions=['gntp'])
import platform
import re
import subprocess
import argparse
from pathlib import Path
from packaging import version
from packaging.specifiers import SpecifierSet
from importlib import metadata
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich import traceback as rtraceback
from gntp.notifier import GrowlNotifier
from licface import CustomRichHelpFormatter
from typing import Set, Optional, List

rtraceback.install(show_locals=False, width=os.get_terminal_size()[0], theme='fruity', word_wrap=True)

REQ_FILE = "requirements.txt"
REQ_INSTALL_FILE = "requirements-install.txt"
console = Console()

# Growl notifier setup
growl = GrowlNotifier(
    applicationName="Package Checker",
    notifications=["Update", "Info", "Error"],
    defaultNotifications=["Update"]
)
growl.register()


def send_growl(title, message, priority=1):
    """Send notification via Growl."""
    try:
        growl.notify(
            noteType="Update",
            title=title,
            description=message,
            sticky=False,
            priority=priority
        )
    except Exception as e:
        console.print(f"[red]Growl error:[/red] {e}")


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
        console.print(f"[red]❌ Install error:[/red] {e}")
        send_growl("Install Error", f"Failed from {file_path}", priority=2)

        if force_retry:
            console.print("[yellow]Retrying installation (force mode)...[/yellow]")
            return run_pip_install_from_file(file_path, force_retry=False)

        if Confirm.ask("Retry installation?"):
            return run_pip_install_from_file(file_path, force_retry=False)

        return False


def run_pip_install(packages, force_retry=False):
    """Run pip install for a list of packages, saving them to requirements-install.txt."""
    # Save to requirements-install.txt
    with open(REQ_INSTALL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(packages))

    return run_pip_install_from_file(REQ_INSTALL_FILE, force_retry=force_retry)


def check_packages(reqs, force_retry=False, force_install=False, summary_only=False, show=True):
    """Check installed packages vs requirements and collect installs if needed."""
    logger.warning(f"reqs: {reqs}")
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
                            console.print(f"[red]❌ Install error:[/red] {e}")
                            send_growl("Install Error", f"Failed to install {pkg}", priority=2)
        return reqs

    if show:
        table = Table(title="Package Version Checker", header_style="bold white")
        table.add_column("Package", style="bold")
        table.add_column("Installed", style="cyan")
        table.add_column("Required", style="magenta")
        table.add_column("", style="bold")  # emoji column
        table.add_column("Status")

    to_install = []  # collect install/upgrade/downgrade tasks

    for pkg, spec in reqs:
        try:
            inst_ver = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            inst_ver = None

        status = ""
        status_num = 0
        emoji = ""

        if inst_ver is None:
            status = "[red]Not Installed[/red]"
            emoji = "❌"
            if not summary_only:
                send_growl(f"{pkg} Missing", f"{pkg} is not installed.")
            if not summary_only and Confirm.ask(f"Install {pkg} (found none) {spec or ''}?"):
                to_install.append(f"{pkg}{spec or ''}")
            table.add_row(pkg, "", spec or "-", emoji, status)
            continue

        iv = version.parse(inst_ver)
        if spec:
            spec_set = SpecifierSet(spec)

            if "==" in spec:  # exact match required
                req_ver = spec.split("==")[1]
                if iv == version.parse(req_ver):
                    emoji = "✅"
                    status = "[#AAAAFF]Exact match[/]"
                    if not summary_only:
                        send_growl(f"{pkg} OK", f"{pkg} {inst_ver} matches {spec}")
                else:
                    emoji = "⚠"
                    status = f"[#FFFF00]Mismatch (need {spec})[/]"
                    if not summary_only:
                        send_growl(f"{pkg} Mismatch", f"{pkg} {inst_ver} != required {spec}")
                    if not summary_only and Confirm.ask(f"Change {pkg} (found {inst_ver}) to {spec}?"):
                        to_install.append(f"{pkg}{spec}")
            else:
                if iv in spec_set:
                    emoji = "✅"
                    status = f"[#AAAAFF]OK (within {spec})[/]"
                    if not summary_only:
                        send_growl(f"{pkg} OK", f"{pkg} {inst_ver} satisfies {spec}")
                else:
                    emoji = "⚠"
                    status = f"[#FFFF00]Not in range {spec}[/]"
                    if not summary_only:
                        send_growl(f"{pkg} Out of range", f"{pkg} {inst_ver} not in {spec}")
                    if not summary_only and Confirm.ask(f"Install {pkg} (found {inst_ver}) {spec}?"):
                        to_install.append(f"{pkg}{spec}")
        else:
            emoji = "✅"
            status = "[#AAAAFF]No version rule[/]"
            if not summary_only:
                send_growl(f"{pkg} Checked", f"{pkg} {inst_ver}")

        table.add_row(pkg, inst_ver or "-", spec or "-", emoji, status)

    if show:
        console.print(table)

    if summary_only:
        # Do not install anything in summary mode
        return []

    if to_install and show:
        console.print(f"[yellow]Installing these packages:[/yellow] {', '.join(to_install)}")
        success = run_pip_install(to_install, force_retry=force_retry)
        if not success:
            console.print("[red]Some packages failed to install.[/red]")
    else:
        console.print("[green]All requirements satisfied. Nothing to install.[/green]")

    return to_install

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
    dep = dep_string.split('[')[0].split(';')[0].strip()
    for op in ['>=', '<=', '==', '!=', '~=', '>', '<']:
        dep = dep.split(op)[0]
    return dep.lower() if dep else None

def _extract_from_list_node(node) -> Set[str]:
    deps = set()
    if isinstance(node, ast.List):
        for elt in node.elts:
            val = elt.value if isinstance(elt, ast.Constant) else \
                  elt.s if hasattr(elt, 's') else None
            if val:
                logger.notice(f"val: {val}")
                # pkg = _extract_package_name(val)
                # if pkg: deps.add(pkg)
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

    # raise ValueError(f"Unsupported spec: {spec}")
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
        return f">={major}.0,< {major+1}.0"

    # "1.2.*" → >=1.2.0,<1.3.0
    if len(parts) == 3 and parts[2] == "*":
        minor = int(parts[1])
        return f">={major}.{minor}.0,<{major}.{minor+1}.0"

    # raise ValueError(f"Unsupported wildcard: {spec}")
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
                # pkg = _extract_package_name(dep)
                # if pkg: deps.add(pkg)
                logger.warning(f"dep: {dep}")
                deps.add(pkg)
        if 'tool' in data and 'poetry' in data['tool']:
            poetry = data['tool']['poetry']
            logger.warning(f"poetry: {poetry}")
            for key in ['dependencies']:#, 'dev-dependencies']:
                if key in poetry:
                    for dep, ver in poetry[key].items():
                        if isinstance(ver, dict):
                            ver = ver.get('version')
                        logger.alert(f"dep: {dep}")
                        logger.alert(f"ver: {ver}")
                        spec = convert_spec(ver)
                        logger.alert(f"spec: {spec}")
                        if dep != 'python':
                            # logger.alert(f"dep: {dep}")
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
    if not path.exists():
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
        console.print(f"[bold yellow]Warning: Could not parse setup.py:[/] {e}")
        if str(os.getenv('TRACEBACK', '0').lower()) in ['1', 'yes', 'true']:
            tprint(*sys.exc_info(), None, False, True)
    logger.notice(f"deps: {deps}")
    return deps

def main():
    global REQ_FILE
    parser = argparse.ArgumentParser(description="Package requirements checker", formatter_class=CustomRichHelpFormatter, prog='pipr')

    parser.add_argument('FILE', nargs='?', help="requirements file")
    parser.add_argument("-f", "--force-retry", action="store_true",
                        help="Force retry installation automatically if error occurs")
    parser.add_argument("-F", '--force-install', action="store_true",
                        help="Force install packages without asking for confirmation")
    parser.add_argument("-s", "--summary", action="store_true",
                        help="Show summary table only (non-interactive, no install)")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Debugging process (logging)")

    args = parser.parse_args()

    # os.environ.update({'NO_LOGGING':'1'})
    # try:
    #     os.environ.pop('LOGGING')
    # except:
    #     pass

    if args.debug:
        try:
            os.environ.pop('NO_LOGGING')
        except:
            pass
        os.environ.update({'LOGGING':'1'})

    if args.FILE:
        REQ_FILE = args.FILE

    requirement_files = [
        Path.cwd() / 'setup.py',
        Path.cwd() / 'pyproject.toml',
        Path.cwd() / REQ_FILE,
        Path.cwd() / REQ_INSTALL_FILE,
    ]

    REQ_FOUND = []
    requirements = []

    for i in requirement_files:
        if Path(i).exists() and Path(i).stat().st_size > 0:
            REQ_FOUND.append(Path(i))

    # If requirements-install.txt exists and is not empty -> install directly
    # if Path(REQ_INSTALL_FILE).exists() and Path(REQ_INSTALL_FILE).stat().st_size > 0:
    if Path(REQ_INSTALL_FILE) in REQ_FOUND:
        console.print(f"[yellow]Found {REQ_INSTALL_FILE}, installing directly...[/yellow]")
        run_pip_install_from_file(REQ_INSTALL_FILE, force_retry=args.force_retry)
        sys.exit(0)

    if not args.FILE:
        # if not Path(REQ_FILE).exists():
        if not REQ_FOUND:
            # console.print(f"\n:cross_mark: [red]File {REQ_FILE} not found![/red]\n")
            console.print(f"\n:cross_mark: [red]No one requirements files found![/red]\n")
            parser.print_help()
            sys.exit(1)

        requirements = parse_setup_py()
        logger.warning(f"requirements: {requirements}")
        if len(requirements) < 1:
            console.print(f"\n:cross_mark: [#FFFF00]'setup.py' has no requirements or no file ![/]")
            console.print(f"\n🚀 [#00FFFF]try to get from 'pyproject.toml' ...[/]")
            requirements = parse_pyproject_toml()
            logger.warning(f"requirements: {requirements}")
            if len(requirements) < 1:
                console.print(f"\n:cross_mark: [#FFFF00]'pyproject.toml' has no requirements or no file ![/]")
    logger.emergency(f"requirements: {requirements}")
    if len(requirements) < 1:
        if not Path(REQ_FILE).exists():
            console.print(f"\n:cross_mark: [red bold]File {REQ_FILE} not found![/]\n")
            parser.print_help()
            sys.exit(1)
        logger.notice(f"REQ_FILE: {REQ_FILE}")
        requirements = parse_requirements(REQ_FILE)
        logger.warning(f"requirements: {requirements}")
        if len(requirements) < 1:
            console.print(f"\n:cross_mark: [#FFFF00]requirements.txt is empty ![/]")
            sys.exit(1)

    check_packages(
        requirements,
        force_retry=args.force_retry,
        force_install=args.force_install,
        summary_only=args.summary
    )


if __name__ == "__main__":
    main()