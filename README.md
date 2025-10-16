# 📦 PIPR - Python Package Requirements Checker

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 🔍 A smart Python package requirements checker that validates, installs, and manages your project dependencies with style!

## ✨ Features

- 🎯 **Smart Requirements Parsing** - Handles complex version specifiers and conditional markers
- 📊 **Beautiful Table Display** - Rich terminal output with colors and emojis
- 🔄 **Interactive Installation** - Prompts for confirmation before installing/upgrading packages
- 📱 **Growl Notifications** - Desktop notifications for package status updates
- 🛠️ **Batch Installation** - Efficiently handles multiple package installations
- 🎨 **Rich CLI Interface** - Enhanced help formatting and error display
- 🔧 **Platform-Aware** - Handles platform-specific dependencies (Windows, Linux, etc.)
- ⚡ **Force Retry Mode** - Automatic retry mechanism for failed installations

## 🚀 Installation

### Prerequisites

Install the required dependencies:

```bash
pip install rich packaging gntp licface
```

### Quick Install

1. Download `pipr.py`
2. Make it executable:
   ```bash
   chmod +x pipr.py
   ```
3. Optionally, add to your PATH or create an alias

4. or use `pip`
```bash
   pip install git+https://github.com/cumulus13/pipr
```
## 📋 Usage

### Basic Usage

Place the script in your project directory with a `requirements.txt` file:

```bash
python pipr.py
```

### Command Line Options

```bash
python pipr.py --help
```

| Option                | Description                                          |
|-----------------------|------------------------------------------------------|
| `-f, --force-retry`   | Force retry installation automatically               |
|                       |     if error occurs                                  |
| `-F, --force-install` | Force install packages without asking for            |
|                       |     confirmation                                     |
| `-s, --summary`       | Show summary table only (non-interactive, no install)|

### Requirements File Format

The tool supports standard `requirements.txt` format with additional features:

```txt
# Basic package
requests

# Version specifiers
numpy>=1.20.0
pandas==1.3.0
matplotlib>3.0,<4.0

# Platform-specific dependencies
pywin32>=227; sys_platform == "win32"
uvloop>=0.14; sys_platform == "linux"

# Comments are supported
flask  # Web framework
```

## 🎮 Interactive Features

### 📊 Status Display

The tool displays a beautiful table showing:

- 📦 **Package Name**
- 💾 **Installed Version**
- 🎯 **Required Version**
- 😀 **Status Emoji** (✅ ❌ ⚠️ ℹ️)
- 📄 **Detailed Status**

### 🤝 Interactive Prompts

- **Missing Package**: Asks if you want to install
- **Version Mismatch**: Asks if you want to upgrade/downgrade
- **Failed Installation**: Offers retry option

### 📱 Desktop Notifications

Receive Growl notifications for:
- ✅ Successful installations
- ❌ Installation errors  
- ℹ️ Package status updates
- ⚠️ Version mismatches

## 🔧 Advanced Features

### 🎯 Version Matching Logic

- **Exact Match (`==`)**: Ensures precise version alignment
- **Range Matching (`>=`, `>`, `<`, `<=`)**: Flexible version ranges
- **Compatible Release (`~=`)**: Semantic version compatibility
- **Complex Specifiers**: Multiple conditions with commas

### 🖥️ Platform Awareness

Automatically handles platform-specific dependencies:
- Windows-only packages
- Linux-specific requirements
- Cross-platform compatibility checks

### 📁 File Management

- **`requirements.txt`**: Main requirements file
- **`requirements-install.txt`**: Temporary install queue (auto-cleaned)

## 💡 Workflow

1. **📖 Parse Requirements** - Reads and validates `requirements.txt`
2. **🔍 Check Installed** - Compares with currently installed packages
3. **📊 Display Table** - Shows comprehensive status overview
4. **🤔 Interactive Prompts** - Asks for user confirmation on changes
5. **⚡ Batch Install** - Efficiently installs multiple packages
6. **📱 Notify Results** - Sends desktop notifications
7. **🧹 Cleanup** - Removes temporary files

## 📈 Example Output

```
                Package Version Checker                
┏━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Package   ┃ Installed ┃ Required ┃     ┃ Status              ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ requests  │ 2.28.1    │ >=2.25.0 │ ✅ │ OK (within >=2.25.0)│
│ numpy     │ none      │ >=1.20.0 │ ❌ │ Not Installed       │
│ pandas    │ 1.2.0     │ ==1.3.0  │ ⚠️ │ Mismatch (need ==…) │
└───────────┴───────────┴──────────┴─────┴─────────────────────┘
```

## 🛠️ Error Handling

- **🔄 Automatic Retry** - Built-in retry mechanism for failed installations
- **📝 Rich Tracebacks** - Beautiful error formatting with context
- **⚠️ Graceful Degradation** - Continues processing even if some packages fail
- **🧹 Cleanup on Failure** - Removes temporary files on errors

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Hadi Cahyadi** - [cumulus13@gmail.com](mailto:cumulus13@gmail.com)

## 🙏 Acknowledgments

- 🎨 [Rich](https://github.com/willmcgugan/rich) - Beautiful terminal output
- 📦 [Packaging](https://github.com/pypa/packaging) - Version parsing utilities
- 📱 [GNTP](https://github.com/kfdm/gntp) - Growl notification protocol
- 🎭 [Licface](https://github.com/cumulus13/licface) - Custom help formatting

---


[![Buy Me a Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/cumulus13)

[![Donate via Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/cumulus13)

[Support me on Patreon](https://www.patreon.com/cumulus13)

[Medium](https://medium.com/@cumulus13/pipr-the-python-package-manager-you-never-knew-you-needed-336088218236?postPublishedType=initial)

⭐ **Star this repository if you find it helpful!**