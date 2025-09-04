import os
import zipfile
from datetime import datetime

# Get current timestamp for filename
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
backup_filename = f"majicmall_backup_{timestamp}.zip"

# Paths to exclude from backup
exclude_dirs = {'venv', '.git', '__pycache__', 'node_modules', '.github'}

def should_include(file_path):
    for ex in exclude_dirs:
        if f"/{ex}/" in file_path or file_path.startswith(f"{ex}/"):
            return False
    return True

def zip_project(root_dir, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(root_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                rel_path = os.path.relpath(file_path, root_dir)
                if should_include(rel_path):
                    zipf.write(file_path, rel_path)

if __name__ == "__main__":
    print("📦 Creating backup...")
    zip_project(".", backup_filename)
    print(f"✅ Backup created: {backup_filename}")
