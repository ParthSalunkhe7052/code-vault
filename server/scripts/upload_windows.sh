windows_status=$(cat /workspace/build_status_windows 2>/dev/null || echo "pending")
if [[ "$windows_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Windows upload (status: $windows_status)"
  exit 0
fi
windows_artifact=$(cat /workspace/windows_artifacts 2>/dev/null)
if [ -z "$windows_artifact" ]; then
  exit 0
fi

max_retries=3
retry_count=0
upload_success=false
while [ $retry_count -lt $max_retries ] && [ "$upload_success" = "false" ]; do
  if [ $retry_count -gt 0 ]; then
    echo "[Cloud Build] Retrying Windows upload (attempt $((retry_count+1))/$max_retries)..."
    sleep 2
  fi
  echo "[Cloud Build] Uploading Windows: $windows_artifact"
  if gsutil cp "/workspace/$windows_artifact" "gs://{gcs_bucket}/builds/{build_id}/windows/$windows_artifact" 2>/dev/null; then
    upload_success=true
    echo "[Cloud Build] Windows upload successful"
  else
    retry_count=$((retry_count+1))
  fi
done
if [ "$upload_success" != "true" ]; then
  echo "[Cloud Build] Windows upload failed after $max_retries attempts"
  exit 1
fi
