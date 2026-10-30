import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

try:
    from huggingface_hub import snapshot_download
    path = snapshot_download(repo_id="Systran/faster-whisper-base", local_files_only=False)
    print(f"DOWNLOAD_SUCCESS: {path}")
except Exception as e:
    print(f"DOWNLOAD_FAILED: {e}")
