#!/usr/bin/env python
#author: Hadi Cahyadi <cumulus13@gmail.com>
#license: MIT

import os
import sys
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

rtraceback.install(show_locals = False, width=os.get_terminal_size()[0], theme = 'fruity', word_wrap=True)

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
            if match:
                name, spec = match.groups()
                spec = spec.strip()
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


def check_packages(reqs, force_retry=False, force_install=False):
    """Check installed packages vs requirements and collect installs if needed."""
    
    if force_install:
        for pkg, spec in reqs:
            run_pip_install([f"{pkg}{spec or ''}"], force_retry=force_retry)
        return reqs
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
        emoji = ""

        if inst_ver is None:
            status = "[red]Not Installed[/red]"
            emoji = "❌"
            send_growl(f"{pkg} Missing", f"{pkg} is not installed.")
            if Confirm.ask(f"Install {pkg} (found none) {spec or ''}?"):
                to_install.append(f"{pkg}{spec or ''}")
            table.add_row(pkg, "none", spec or "-", emoji, status)
            continue

        iv = version.parse(inst_ver)
        if spec:
            spec_set = SpecifierSet(spec)

            if "==" in spec:  # exact match required
                req_ver = spec.split("==")[1]
                if iv == version.parse(req_ver):
                    emoji = "ℹ️"
                    status = "[#AAAAFF]Exact match[/]"
                    send_growl(f"{pkg} OK", f"{pkg} {inst_ver} matches {spec}")
                else:
                    emoji = "⚠️"
                    status = f"[#FFFF00]Mismatch (need {spec})[/]"
                    send_growl(f"{pkg} Mismatch", f"{pkg} {inst_ver} != required {spec}")
                    if Confirm.ask(f"Change {pkg} (found {inst_ver}) to {spec}?"):
                        to_install.append(f"{pkg}{spec}")
            else:
                if iv in spec_set:
                    emoji = "ℹ️"
                    status = f"[#AAAAFF]OK (within {spec})[/]"
                    send_growl(f"{pkg} OK", f"{pkg} {inst_ver} satisfies {spec}")
                else:
                    emoji = "⚠️"
                    status = f"[#FFFF00]Not in range {spec}[/]"
                    send_growl(f"{pkg} Out of range", f"{pkg} {inst_ver} not in {spec}")
                    if Confirm.ask(f"Install {pkg} (found {inst_ver}) {spec}?"):
                        to_install.append(f"{pkg}{spec}")
        else:
            emoji = "ℹ️"
            status = "[#AAAAFF]No version rule[/]"
            send_growl(f"{pkg} Checked", f"{pkg} {inst_ver}")

        table.add_row(pkg, inst_ver or "none", spec or "-", emoji, status)

    console.print(table)

    if to_install:
        console.print(f"[yellow]Installing these packages:[/yellow] {', '.join(to_install)}")
        success = run_pip_install(to_install, force_retry=force_retry)
        if not success:
            console.print("[red]Some packages failed to install.[/red]")
    else:
        console.print("[green]All requirements satisfied. Nothing to install.[/green]")

    return to_install

def main():
    parser = argparse.ArgumentParser(description="Package requirements checker", formatter_class=CustomRichHelpFormatter, prog='pipr')
    parser.add_argument("-f", "--force-retry", action="store_true",
                        help="Force retry installation automatically if error occurs")
    parser.add_argument("-F", '--force-install', action="store_true",
                        help="Force install packages without asking for confirmation")
    args = parser.parse_args()

    # If requirements-install.txt exists and is not empty -> install directly
    if Path(REQ_INSTALL_FILE).exists() and Path(REQ_INSTALL_FILE).stat().st_size > 0:
        console.print(f"[yellow]Found {REQ_INSTALL_FILE}, installing directly...[/yellow]")
        run_pip_install_from_file(REQ_INSTALL_FILE, force_retry=args.force_retry)
        sys.exit(0)

    if not Path(REQ_FILE).exists():
        console.print(f"\n:cross_mark: [red]File {REQ_FILE} not found![/red]\n")
        parser.print_help()
        sys.exit(1)

    requirements = parse_requirements(REQ_FILE)
    if len(requirements) < 1:
        console.print(f"\n:cross_mark: [#FFFF00]requirements.txt is empty ![/]")
        sys.exit(1)

    check_packages(requirements, force_retry=args.force_retry, force_install=args.force_install)

if __name__ == "__main__":
    main()