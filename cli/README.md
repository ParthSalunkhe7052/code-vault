# License Wrapper CLI Compiler

A command-line tool for compiling Python applications with license protection locally on your machine.

## 🚀 Quick Start

### 1. Prerequisites

Make sure you have Python 3.8+ and Nuitka installed:

```bash
pip install nuitka requests
```

### 2. Check Status

```bash
python lw_compiler.py status
```

This will show if you're logged in, if Nuitka is installed, and other environment info.

### 3. Login

```bash
python lw_compiler.py login
```

Enter your License Wrapper account credentials when prompted.

### 4. Build a Project

**Interactive mode:**
```bash
python lw_compiler.py build
```

**Direct mode:**
```bash
python lw_compiler.py build PROJECT_ID --license LIC-XXXX-XXXX-XXXX
```

## 📋 Commands

| Command | Description |
|---------|-------------|
| `login` | Login with your License Wrapper account |
| `logout` | Clear saved credentials |
| `projects` | List your projects |
| `licenses PROJECT_ID` | List licenses for a project |
| `build [PROJECT_ID]` | Build a project locally |
| `status` | Show login status and environment info |

## 🔧 Build Options

```bash
python lw_compiler.py build PROJECT_ID [options]

Options:
  -l, --license KEY    License key to embed in the build
```

## 📁 Output

Compiled executables are saved to the `./output/` directory.

## ⚠️ First Run

The first compilation may take longer (5-15 minutes) because Nuitka downloads required components (C compiler, etc.). Subsequent builds are faster.

## 🐛 Troubleshooting

### "Nuitka not found"
Install Nuitka: `pip install nuitka`

Run `python lw_compiler.py status` to check your environment.

### "Could not connect to server"
Check that the License Wrapper server is running and accessible.

### Compilation fails
- Make sure your Python code runs correctly before compiling
- Check for syntax errors in your source files
- Some packages may not be compatible with Nuitka

### Colors not showing on Windows
The CLI automatically enables ANSI colors. If colors still don't work, try using Windows Terminal or PowerShell 7+.

## 📝 License

Part of the License Wrapper project.

