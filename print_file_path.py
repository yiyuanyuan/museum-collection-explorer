import os

def list_files(root_folder, output_file="all_file_paths.txt"):
    with open(os.path.join(root_folder, output_file), "w", encoding="utf-8") as f:
        for dirpath, dirnames, filenames in os.walk(root_folder):
            # Skip unwanted folders
            dirnames[:] = [d for d in dirnames if d not in ("venv", "node_modules")]

            for filename in filenames:
                # Construct relative path from root folder
                rel_path = os.path.relpath(os.path.join(dirpath, filename), root_folder)
                f.write(rel_path + "\n")

if __name__ == "__main__":
    root_folder = os.path.dirname(os.path.abspath(__file__))  # use the script’s folder
    list_files(root_folder)
    print("All file paths written to all_file_paths.txt")
