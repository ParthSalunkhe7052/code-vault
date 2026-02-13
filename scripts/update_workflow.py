
file_path = '.github/workflows/cloud-compile.yml'

# New Unix content blocks
linux_deps_new = """      - name: Install project dependencies (Python)
        if: ${{ github.event.inputs.language == 'python' }}
        run: |
          cd project/source
          if [ -f "requirements.txt" ]; then
            echo "Installing dependencies from requirements.txt..."
            # Filter out ta-lib which requires system libraries
            grep -vE '^\s*(ta-lib|TA-Lib)\s*' requirements.txt > requirements_filtered.txt || true
            
            if [ -s requirements_filtered.txt ]; then
              pip install -r requirements_filtered.txt
            fi
            
            # Check if ta-lib was in requirements
            if grep -qE '^\s*(ta-lib|TA-Lib)\s*' requirements.txt; then
              echo "WARNING: ta-lib requires system libraries. Skipping ta-lib installation."
              echo "TALIB_SKIPPED=true" >> $GITHUB_ENV
            fi
          else
            echo "No requirements.txt found, skipping dependency install"
          fi"""

linux_notify_new = """      - name: Notify completion
        if: always()
        continue-on-error: true
        run: |
          if [ -n "$UPLOAD_KEY" ]; then status="completed"; else status="failed"; fi
          
          # Capture detailed error message
          error_msg=""
          if [ "$status" = "failed" ]; then
            if [ "$TALIB_SKIPPED" = "true" ]; then
              error_msg="Build failed: Project requires ta-lib which needs system libraries. Please remove ta-lib dependency."
            else
              error_msg="Compilation failed. Check GitHub Actions logs."
            fi
          fi
          
          payload=$(cat <<EOF
          {
            "build_id": "${{ github.event.inputs.build_id }}",
            "platform": "linux",
            "status": "$status",
            "download_key": "$UPLOAD_KEY",
            "filename": "$UPLOAD_FILENAME",
            "error": $(if [ -n "$error_msg" ]; then echo "\"$error_msg\""; else echo "null"; fi),
            "github_run_url": "https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          }
          EOF
          )
          
          signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "${{ github.event.inputs.callback_secret }}" | awk '{print $2}')
          
          # Retry webhook delivery
          max_retries=3
          retry_count=0
          success=false
          
          while [ "$success" = "false" ] && [ $retry_count -lt $max_retries ]; do
            if curl -X POST "${{ github.event.inputs.callback_url }}" \
              -H "Content-Type: application/json" \
              -H "X-Signature: $signature" \
              -d "$payload" \
              --max-time 10 \
              --fail-with-body; then
              success=true
            else
              retry_count=$((retry_count + 1))
              if [ $retry_count -lt $max_retries ]; then
                sleep 2
              fi
            fi
          done
          
          if [ "$success" = "false" ]; then
            echo "ERROR: Failed to deliver webhook after $max_retries attempts"
            echo "Build status: $status"
            exit 1
          fi"""

macos_deps_new = """      - name: Install project dependencies (Python)
        if: ${{ github.event.inputs.language == 'python' }}
        run: |
          cd project/source
          if [ -f "requirements.txt" ]; then
            echo "Installing dependencies from requirements.txt..."
            # Filter out ta-lib which requires system libraries
            grep -vE '^\s*(ta-lib|TA-Lib)\s*' requirements.txt > requirements_filtered.txt || true
            
            if [ -s requirements_filtered.txt ]; then
              pip install -r requirements_filtered.txt
            fi
            
            # Check if ta-lib was in requirements
            if grep -qE '^\s*(ta-lib|TA-Lib)\s*' requirements.txt; then
              echo "WARNING: ta-lib requires system libraries. Skipping ta-lib installation."
              echo "TALIB_SKIPPED=true" >> $GITHUB_ENV
            fi
          else
            echo "No requirements.txt found, skipping dependency install"
          fi"""

macos_notify_new = """      - name: Notify completion
        if: always()
        continue-on-error: true
        run: |
          if [ -n "$UPLOAD_KEY" ]; then status="completed"; else status="failed"; fi
          
          # Capture detailed error message
          error_msg=""
          if [ "$status" = "failed" ]; then
            if [ "$TALIB_SKIPPED" = "true" ]; then
              error_msg="Build failed: Project requires ta-lib which needs system libraries. Please remove ta-lib dependency."
            else
              error_msg="Compilation failed. Check GitHub Actions logs."
            fi
          fi
          
          payload=$(cat <<EOF
          {
            "build_id": "${{ github.event.inputs.build_id }}",
            "platform": "macos",
            "status": "$status",
            "download_key": "$UPLOAD_KEY",
            "filename": "$UPLOAD_FILENAME",
            "error": $(if [ -n "$error_msg" ]; then echo "\"$error_msg\""; else echo "null"; fi),
            "github_run_url": "https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          }
          EOF
          )
          
          signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "${{ github.event.inputs.callback_secret }}" | awk '{print $2}')
          
          # Retry webhook delivery
          max_retries=3
          retry_count=0
          success=false
          
          while [ "$success" = "false" ] && [ $retry_count -lt $max_retries ]; do
            if curl -X POST "${{ github.event.inputs.callback_url }}" \
              -H "Content-Type: application/json" \
              -H "X-Signature: $signature" \
              -d "$payload" \
              --max-time 10 \
              --fail-with-body; then
              success=true
            else
              retry_count=$((retry_count + 1))
              if [ $retry_count -lt $max_retries ]; then
                sleep 2
              fi
            fi
          done
          
          if [ "$success" = "false" ]; then
            echo "ERROR: Failed to deliver webhook after $max_retries attempts"
            echo "Build status: $status"
            exit 1
          fi"""

# Read current file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Linux sections
linux_deps_old = """      - name: Install project dependencies (Python)
        if: ${{ github.event.inputs.language == 'python' }}
        run: |
          cd project/source
          if [ -f "requirements.txt" ]; then
            echo "Installing dependencies from requirements.txt..."
            pip install -r requirements.txt
          else
            echo "No requirements.txt found, skipping dependency install"
          fi"""

linux_notify_old = """      - name: Notify completion
        if: always()
        continue-on-error: true
        run: |
          if [ -n "$UPLOAD_KEY" ]; then status="completed"; else status="failed"; fi
          
          payload=$(cat << EOF
          {
            "build_id": "${{ github.event.inputs.build_id }}",
            "platform": "linux",
            "status": "$status",
            "download_key": "$UPLOAD_KEY",
            "filename": "$UPLOAD_FILENAME",
            "error": null
          }
          EOF
          )
          
          signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "${{ github.event.inputs.callback_secret }}" | awk '{print $2}')
          
          curl -X POST "${{ github.event.inputs.callback_url }}" \
            -H "Content-Type: application/json" \
            -H "X-Signature: $signature" \
            -d "$payload"
"""

if linux_deps_old in content:
    content = content.replace(linux_deps_old, linux_deps_new)
    print("Replaced Linux dependencies")

if linux_notify_old.strip() in content:
    content = content.replace(linux_notify_old.strip(), linux_notify_new)
    print("Replaced Linux notification")
else:
    # Try finding it with tighter strip
    linux_notify_block = content[content.find("build-linux"):]
    notify_start = linux_notify_block.find("- name: Notify completion")
    if notify_start > 0:
         print("Found Linux notification block start")

# Replace MacOS sections
macos_deps_old = """      - name: Install project dependencies (Python)
        if: ${{ github.event.inputs.language == 'python' }}
        run: |
          cd project/source
          if [ -f "requirements.txt" ]; then
            echo "Installing dependencies from requirements.txt..."
            pip install -r requirements.txt
          else
            echo "No requirements.txt found, skipping dependency install"
          fi"""

macos_notify_old = """      - name: Notify completion
        if: always()
        continue-on-error: true
        run: |
          if [ -n "$UPLOAD_KEY" ]; then status="completed"; else status="failed"; fi
          
          payload=$(cat << EOF
          {
            "build_id": "${{ github.event.inputs.build_id }}",
            "platform": "macos",
            "status": "$status",
            "download_key": "$UPLOAD_KEY",
            "filename": "$UPLOAD_FILENAME",
            "error": null
          }
          EOF
          )
          
          signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "${{ github.event.inputs.callback_secret }}" | awk '{print $2}')
          
          curl -X POST "${{ github.event.inputs.callback_url }}" \
            -H "Content-Type: application/json" \
            -H "X-Signature: $signature" \
            -d "$payload"
"""

if macos_deps_old in content:
    content = content.replace(macos_deps_old, macos_deps_new)
    print("Replaced MacOS dependencies")

if macos_notify_old.strip() in content:
    content = content.replace(macos_notify_old.strip(), macos_notify_new)
    print("Replaced MacOS notification")

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
