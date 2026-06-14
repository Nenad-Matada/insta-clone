import uuid
import random
import string
from datetime import datetime

def generate_random_story_url(original_filename: str) -> str:
    """Generate a random URL for story storage - teammates will handle actual file storage"""
    # Generate random unique ID
    random_id = str(uuid.uuid4()).replace("-", "")[:16]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Get file extension
    ext = original_filename.split(".")[-1] if "." in original_filename else "jpg"
    
    # Return URL (need to map this to actual storage)
    return f"stories/{timestamp}_{random_id}.{ext}"

def generate_random_post_url(original_filename: str) -> str:
    """Generate random URL for post media"""
    random_id = str(uuid.uuid4()).replace("-", "")[:16]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    ext = original_filename.split(".")[-1] if "." in original_filename else "jpg"
    return f"posts/{timestamp}_{random_id}.{ext}"