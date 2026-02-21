import os
from io import BytesIO
from PIL import Image

MAX_IMAGE_SIZE = 500

def resize_image(content: bytes, max_size: int = MAX_IMAGE_SIZE) -> tuple:
    """Resize image to max_size on longest side. Returns (content, extension)."""
    img = Image.open(BytesIO(content))
    
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    output = BytesIO()
    img.save(output, format='JPEG', quality=85)
    output.seek(0)
    
    return output.getvalue(), 'jpg'
