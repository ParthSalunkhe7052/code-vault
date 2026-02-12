# CodeVault CLI - Local Source Selection Feature

## 🎯 What Changed

When building a project, if the server bundle is not available or download fails, the CLI now **prompts you to select the source files manually** instead of crashing!

## 🎨 How It Works

### Build Flow (Updated)

1. **Check Local Files** (if available from project data)
   - Shows: "Found local project files at: [path]"
   - Asks: "Use these local files? (Y/n)"

2. **Try API Download**
   - Attempts to download bundle from server
   - Shows progress if available

3. **If Download Fails** ← **NEW!**
   - Shows error message
   - Asks: "How would you like to provide the source files?"
   - Options:
     - **[1]** Browse for a ZIP file (opens file dialog)
     - **[2]** Browse for a project folder (opens folder dialog)
     - **[3]** Type the path manually
     - **[4]** Cancel build

## 📋 Example Interaction

```
[INFO] Attempting to download project bundle from server...

[yellow]Download failed: Server returned HTTP 404[/yellow]
[INFO] The server bundle is not available.

Source Selection for 'Nautika Complex'
============================================================

How would you like to provide the source files?

  [1] Browse for a ZIP file
  [2] Browse for a project folder
  [3] Type the path manually
  [4] Cancel build

Enter your choice (1-4): 2

[dim]Opening folder browser...[/dim]
[OK] Selected: C:\Users\parth\Desktop\Nautika-Complex

[INFO] Copying project folder...
[OK] Copied to: C:\Users\parth\AppData\Local\Temp\tmp123\project

Starting build...
```

## 🖱️ File Browser Dialog

When you select options 1 or 2, a **native file explorer dialog** opens:

- **Option 1 (ZIP file)**: Shows file browser filtered for .zip files
- **Option 2 (Folder)**: Shows folder browser to select project directory

The dialog uses your operating system's native file picker:
- Windows: Windows Explorer style
- macOS: Finder style  
- Linux: GTK/QT style

## ⌨️ Manual Path Entry

If you select option 3, you can type the path directly:

```
Enter the full path: C:\Users\parth\Downloads\my-project.zip
[OK] Path found: C:\Users\parth\Downloads\my-project.zip
```

## ✅ Supported Source Types

1. **ZIP Files** (.zip)
   - Will be extracted automatically
   - Supports standard zip format

2. **Project Folders**
   - Copied to temp directory
   - Automatically ignores: __pycache__, node_modules, .git, .env, dist, build, output

## 🚀 Use Cases

### Use Case 1: Build from Downloaded ZIP
```
1. Download project ZIP from web dashboard
2. Run: codevault project build --interactive
3. Select your project
4. When prompted, choose option 1 (Browse for ZIP)
5. Select the downloaded ZIP file
6. Build proceeds!
```

### Use Case 2: Build from Local Development Folder
```
1. You have project files at C:\Projects\MyApp
2. Run: codevault project build --interactive
3. Select your project
4. When prompted, choose option 2 (Browse for folder)
5. Select C:\Projects\MyApp
6. Build proceeds!
```

### Use Case 3: Build from Specific Path
```
1. Run: codevault project build --interactive
2. Select your project
3. When prompted, choose option 3 (Type path manually)
4. Enter: .\server\uploads\c4744cff76a813f176718f17c6d8ca0e
5. Build proceeds!
```

## 🔧 Technical Details

### Files Modified
- `cli/codevault_cli/build_runner.py` - Added fallback logic
- `cli/codevault_cli/file_browser.py` - New file browser module
- `cli/codevault_cli/commands/projects.py` - Updated to pass project data

### Key Features
- ✅ Cross-platform file dialogs (Windows, macOS, Linux)
- ✅ Falls back to manual input if GUI not available
- ✅ Validates selected files/folders exist
- ✅ Automatic extraction of ZIP files
- ✅ Smart filtering of unwanted folders
- ✅ Clear error messages if something goes wrong

## 🎉 Benefits

**Before:**
```
[ERROR] FileNotFoundError: bundle.zip not found
Window closes...
```

**After:**
```
Download failed, but that's OK!
You can now choose your source files interactively.
Browse, select, and build! 🎉
```

## 💡 Tips

1. **ZIP files are easiest** - Just download from web dashboard
2. **Keep folder structure** - Make sure your project has all files
3. **Config.json is important** - Include it for proper build settings
4. **Manual path works too** - Copy path from File Explorer and paste

## 🐛 Troubleshooting

### "Tkinter not available"
- File dialog won't open
- Falls back to manual path entry
- Just type the path when prompted

### "Invalid ZIP file"
- ZIP might be corrupted
- Try extracting manually first
- Or use folder option instead

### "Path not found"
- Double-check the path
- Use full absolute path (C:\...)
- Use browse option to avoid typos

## ✨ Future Enhancements

Possible future improvements:
- Remember recently used paths
- Drag-and-drop support
- Recent files list
- Auto-detect project type

---

**This feature makes the CLI much more flexible and user-friendly!**
