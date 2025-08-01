"Made by Werner"

import os

def get_files_from_folder(folder_path: str, extension=None, sort=True):
    """
    Read file names/indexes from a specified folder with additional filtering options.

    Args:
        folder_path (str): Path to the folder to read files from (trailing / or \ will be removed)
        extension (str, optional): Filter files by specific extension (e.g., '.txt')
        sort (bool, optional): Whether to sort the file list

    Returns:
        list: A list of file names in the folder
    """

    # Remove trailing path separators
    
    folder_path = folder_path.rstrip('/\\')
    
    try:
        print (f"Get list of all files in the directory")
        # Get list of all files in the directory
        files = os.listdir(folder_path)
        
        # Filter only files (exclude directories)
        files = [f for f in files if os.path.isfile(os.path.join(folder_path, f))]
        
        # Optional: Filter by extension
        if extension:
            files = [f for f in files if f.endswith(extension)]
        
        # Optional: Sort the list
        if sort:
            files.sort()
        
        return files
    
    except OSError as e: 
        print(f"Error: Invalid folder name or call Werner: {e}")
        return []

    except FileNotFoundError:
        print(f"Error: Folder {folder_path} not found.")
        return []

    except PermissionError:
        print(f"Error: No permission to access folder {folder_path}.")
        return []

# Example usages

_path = r'C:/dev/' # NAS\info
_path = r'C:\\dev\\' # NAS\info

files = get_files_from_folder(_path)
print(f"# All files in a folder:\n{files}")

files = get_files_from_folder(_path, extension='.rtf')
print(f"# Only .rtf files:\n{files}")

files = get_files_from_folder(_path, extension='.txt')
print(f"# Only .txt files:\n{files}")

files = get_files_from_folder(_path, sort=True)
print(f"# All files of folder sorted:\n{files}")

files = get_files_from_folder(_path, sort=False)
print(f"# All files of folder unsorted:\n{files}")
print("## Done ##")

##