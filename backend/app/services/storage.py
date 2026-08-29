import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException
from pathlib import Path

# In a real app, this would use boto3 for S3.
# For now, we use local storage in the backend/storage directory as a mock for object storage.
STORAGE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "storage"

# Ensure storage directory exists
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

async def save_upload_file_mock_s3(upload_file: UploadFile, file_size: int) -> str:
    """
    Saves an uploaded file locally as a mock for S3.
    Returns the storage reference (local path).
    """
    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload_file.content_type}")

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    # Generate a secure random filename to avoid collisions and path traversal
    ext = os.path.splitext(upload_file.filename)[1]
    secure_filename = f"{uuid.uuid4()}{ext}"
    
    file_path = STORAGE_DIR / secure_filename
    
    # Reset file pointer just in case
    await upload_file.seek(0)
    
    async with aiofiles.open(file_path, 'wb') as out_file:
        while content := await upload_file.read(1024 * 1024):  # read in 1MB chunks
            await out_file.write(content)
            
    # Mocking S3 reference
    return f"mock-s3://storage/{secure_filename}"
