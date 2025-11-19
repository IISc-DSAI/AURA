from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="BAAI/bge-large-en-v1.5",
    local_dir="bge-large-en-v1.5",
    local_dir_use_symlinks=False
)
