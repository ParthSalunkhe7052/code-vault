linux_status=$(cat /workspace/build_status_linux 2>/dev/null || echo "pending")
if [[ "$linux_status" != "completed" ]]; then
  echo "[Cloud Build] Skipping Linux upload (status: $linux_status)"
  exit 0
fi
linux_artifact=$(cat /workspace/linux_artifacts 2>/dev/null)
if [ -z "$linux_artifact" ]; then
  exit 0
fi

max_retries=3
retry_count=0
upload_success=false
while [ $retry_count -lt $max_retries ] && [ "$upload_success" = "false" ]; do
  if [ $retry_count -gt 0 ]; then
    echo "[Cloud Build] Retrying Linux upload (attempt $((retry_count+1))/$max_retries)..."
    sleep 2
  fi
  echo "[Cloud Build] Uploading Linux: $linux_artifact"
  if gsutil cp "/workspace/$linux_artifact" "gs://{gcs_bucket}/builds/{build_id}/linux/$linux_artifact" 2>/dev/null; then
    upload_success=true
    echo "[Cloud Build] Linux upload successful"
  else
    retry_count=$((retry_count+1))
  fi
done
if [ "$upload_success" != "true" ]; then
  echo "[Cloud Build] Linux upload failed after $max_retries attempts"
  exit 1
fi
