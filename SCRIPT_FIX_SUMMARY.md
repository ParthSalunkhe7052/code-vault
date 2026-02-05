# Cloud Build Script Fix - Summary

## 🐛 Issue
Windows build failed because `cloud_runner.py` could not be found/downloaded.

**Error:**
```
File "Z:\workspace\.github\scripts\cloud_runner.py", line 1
    <?xml version="1.0" encoding="UTF-8"?><Error><Code>InvalidArgument</Code><Message>Authorization</Message></Error>
```

The download URL was returning an authentication error instead of the script.

---

## ✅ Solution

Instead of downloading the script during the build, it's now **included in the source zip** when files are uploaded.

### Changes Made

#### 1. **Backend - Include Script in Upload** 
**File:** `server/routes/cloud_build_routes.py`

```python
# Copy cloud_runner.py to source directory so it's available in Cloud Build
try:
    script_source = Path(__file__).parent.parent.parent / ".github" / "scripts" / "cloud_runner.py"
    script_dest = source_dir / ".github" / "scripts" / "cloud_runner.py"
    
    if script_source.exists():
        script_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script_source, script_dest)
        logger.info(f"[Upload] Copied cloud_runner.py to source")
except Exception as e:
    logger.warning(f"[Upload] Failed to copy cloud_runner.py: {e}")
```

This copies the script into the source directory before creating the zip, so it's included in the upload.

#### 2. **Cloud Build YAML - Updated Paths**
**File:** `cloudbuild.yaml`

**Linux Build:**
```yaml
# Script is now in ./project/source/.github/scripts/
python3 ./project/source/.github/scripts/cloud_runner.py \
  --config '${_CONFIG_JSON}' \
  --source ./project/source
```

**Windows Build:**
```yaml
# Script is now in ./project/source/.github/scripts/
wine python .github/scripts/cloud_runner.py \
  --config '${_CONFIG_JSON}' \
  --source .
```

Both builds now:
1. Verify the script exists before proceeding
2. Use the correct relative path to the script
3. Fail with clear error if script is missing

---

## 🔄 How It Works Now

1. **User uploads files** → Backend copies `cloud_runner.py` into source
2. **Source zipped** → Script is included in the zip
3. **Zip uploaded to R2** → Script is part of the upload
4. **Cloud Build downloads zip** → Script is extracted with source
5. **Build runs** → Script is available at expected path

---

## 📁 File Structure in Cloud Build

```
/workspace/
├── project/
│   └── source/
│       ├── .github/
│       │   └── scripts/
│       │       └── cloud_runner.py  ← Script included here
│       ├── your_bot.py
│       └── requirements.txt
└── artifacts/
```

---

## ✅ Verification

Build steps now include:
```bash
# Verify cloud_runner.py exists
if [ ! -f "./project/source/.github/scripts/cloud_runner.py" ]; then
  echo "[Cloud Build] ERROR: cloud_runner.py not found in source"
  exit 1
fi
echo "[Cloud Build] Build script found"
```

---

## 🚀 Next Steps

1. **Restart your server** to load the updated code
2. **Upload your TestBot files again** (this will create a new zip with the script included)
3. **Trigger a build** - it should work now!

The script will be automatically included in all future uploads.
