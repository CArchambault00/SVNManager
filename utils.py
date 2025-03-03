import hashlib

def get_md5_checksum(file_path):
    """Returns the MD5 checksum of a given file."""
    md5_hash = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):  # Read in chunks of 4KB
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None