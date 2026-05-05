import os


TARGET_DIR = os.path.dirname(os.path.abspath(__file__))
print(TARGET_DIR)

EXTENSIONS = (".svg", ".png", ".eps", ".gif")

delete_count = 0

for root, dirs, files in os.walk(TARGET_DIR):
    for f in files:
        if f.lower().endswith(EXTENSIONS):
            full_path = os.path.join(root, f)
            try:
                os.remove(full_path)
                delete_count += 1
                print(f"Deleted: {full_path}")
            except Exception as e:
                print(f"Failed to delete {full_path}: {e}")

print(f"\nDone! {delete_count} files deleted.")