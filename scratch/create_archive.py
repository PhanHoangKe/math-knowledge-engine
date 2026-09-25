import zipfile
from pathlib import Path
import hashlib
import shutil

root_dir = Path("d:/Math Knowledge Engine")
output_zip = root_dir / "math_knowledge_engine_dev02a.zip"
artifact_dir = Path(r"C:\Users\kedep\.gemini\antigravity\brain\c66fc0f2-aa80-41a5-9627-ca17d9485124")

excluded_dirs = {".git", ".venv", "__pycache__", ".pytest_cache"}
excluded_extensions = {".zip", ".pyc"}

with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
    for file_path in root_dir.rglob("*"):
        if file_path.is_file():
            # Check exclusions
            parts = file_path.relative_to(root_dir).parts
            if any(p in excluded_dirs for p in parts):
                continue
            if file_path.suffix in excluded_extensions:
                continue
            arcname = file_path.relative_to(root_dir).as_posix()
            zipf.write(file_path, arcname)

hasher = hashlib.sha256()
with open(output_zip, "rb") as f:
    while chunk := f.read(65536):
        hasher.update(chunk)
zip_hash = hasher.hexdigest()

print(f"Archive created: {output_zip}")
print(f"SHA-256: {zip_hash}")
print(f"Size: {output_zip.stat().st_size} bytes")

# Copy to artifacts directory
dest_artifact = artifact_dir / "math_knowledge_engine_dev02a.zip"
shutil.copyfile(output_zip, dest_artifact)
print(f"Copied to artifact dir: {dest_artifact}")
