import hashlib

def get_image_hash(image_bytes: bytes) -> str:
    """
    Computes the SHA256 hash of the given image bytes.
    Returns the hex digest.
    """
    return hashlib.sha256(image_bytes).hexdigest()
