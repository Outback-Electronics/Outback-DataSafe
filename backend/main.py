from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import aiofiles
import os
import uuid
from PIL import Image
import io
from datetime import datetime

from backend.config import settings
from backend.database import Database
from backend.auth import (
    verify_password, get_password_hash, create_access_token, 
    get_current_user
)
from backend.models import (
    UserCreate, UserLogin, UserResponse, Token, FileCreate, 
    FileResponse, PhotoResponse, ShareCreate
)
from backend.ai_processor import PersonManager

# Initialize database and AI manager
db = Database(settings.DATABASE_PATH)
person_manager = PersonManager(db)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create default admin user if not exists
    if db.get_user("admin") is None:
        db.create_user(
            username="admin",
            email="admin@localhost",
            password_hash=get_password_hash("admin123"),
            quota=settings.DEFAULT_USER_QUOTA,
            is_admin=True
        )
    yield

app = FastAPI(title="Outback DataSafe", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (web interface)
app.mount("/static", StaticFiles(directory="web"), name="static")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Authentication endpoints
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user: UserCreate):
    if db.get_user(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    password_hash = get_password_hash(user.password)
    quota = user.quota or settings.DEFAULT_USER_QUOTA
    
    user_id = db.create_user(
        username=user.username,
        email=user.email,
        password_hash=password_hash,
        quota=quota
    )
    
    return UserResponse(**db.get_user_by_id(user_id))

@app.post("/api/auth/login", response_model=Token)
async def login(user: UserLogin):
    db_user = db.get_user(user.username)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(
        data={"sub": db_user["username"], "user_id": db_user["id"]}
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    user = db.get_user_by_id(current_user["user_id"])
    return UserResponse(**user)

# File endpoints
@app.post("/api/files", response_model=FileResponse)
async def create_file(
    file: UploadFile = File(...),
    parent_id: int = Form(None),
    current_user: dict = Depends(get_current_user)
):
    user = db.get_user_by_id(current_user["user_id"])
    
    # Check quota
    if user["used_space"] + file.size > user["quota"]:
        raise HTTPException(status_code=400, detail="Quota exceeded")
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = settings.FILES_DIR / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Get MIME type
    mime_type = file.content_type or "application/octet-stream"
    
    # Create database entry
    file_id = db.create_file(
        user_id=current_user["user_id"],
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file.size,
        mime_type=mime_type,
        parent_id=parent_id
    )
    
    return FileResponse(**db.get_file(file_id))

@app.post("/api/files/directory", response_model=FileResponse)
async def create_directory(
    file_data: FileCreate,
    current_user: dict = Depends(get_current_user)
):
    file_id = db.create_file(
        user_id=current_user["user_id"],
        filename=file_data.filename,
        original_filename=file_data.filename,
        file_path="",
        file_size=0,
        mime_type=None,
        parent_id=file_data.parent_id,
        is_directory=True
    )
    
    return FileResponse(**db.get_file(file_id))

@app.get("/api/files", response_model=List[FileResponse])
async def list_files(
    parent_id: int = None,
    current_user: dict = Depends(get_current_user)
):
    files = db.get_files(current_user["user_id"], parent_id)
    return [FileResponse(**file) for file in files]

@app.get("/api/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    current_user: dict = Depends(get_current_user)
):
    file = db.get_file(file_id)
    if not file or file["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(**file)

@app.get("/api/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: dict = Depends(get_current_user)
):
    file = db.get_file(file_id)
    if not file or file["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="File not found")
    
    if file["is_directory"]:
        raise HTTPException(status_code=400, detail="Cannot download directory")
    
    return FileResponse(
        path=file["file_path"],
        filename=file["original_filename"],
        media_type=file["mime_type"]
    )

@app.delete("/api/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: dict = Depends(get_current_user)
):
    file = db.get_file(file_id)
    if not file or file["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete physical file
    if not file["is_directory"] and os.path.exists(file["file_path"]):
        os.remove(file["file_path"])
    
    db.delete_file(file_id)
    return {"message": "File deleted successfully"}

# Photo endpoints
@app.post("/api/photos", response_model=PhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user = db.get_user_by_id(current_user["user_id"])
    
    # Check file size
    content = await file.read()
    if len(content) > settings.MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.SUPPORTED_PHOTO_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    # Check quota
    if user["used_space"] + len(content) > user["quota"]:
        raise HTTPException(status_code=400, detail="Quota exceeded")
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = settings.PHOTOS_DIR / unique_filename
    thumbnail_path = settings.THUMBNAILS_DIR / f"{uuid.uuid4()}.jpg"
    
    # Save original photo
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Create thumbnail
    try:
        image = Image.open(io.BytesIO(content))
        
        # Convert HEIC to JPEG if needed
        if file_extension == ".heic":
            image = image.convert("RGB")
            file_extension = ".jpg"
            unique_filename = f"{uuid.uuid4()}.jpg"
            file_path = settings.PHOTOS_DIR / unique_filename
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        
        # Get image dimensions
        width, height = image.size
        
        # Create thumbnail
        image.thumbnail((settings.THUMBNAIL_SIZE, settings.THUMBNAIL_SIZE))
        image.save(thumbnail_path, "JPEG", quality=85)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")
    
    # Create file entry
    file_id = db.create_file(
        user_id=current_user["user_id"],
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=f"image/{file_extension[1:]}",
        parent_id=None
    )
    
    # Create photo entry
    photo_id = db.create_photo(
        user_id=current_user["user_id"],
        file_id=file_id,
        file_path=str(file_path),
        width=width,
        height=height
    )
    
    # Update thumbnail path
    db.update_photo_thumbnail(photo_id, str(thumbnail_path))
    
    # Process faces with AI (async to not block upload)
    try:
        person_manager.process_photo_faces(photo_id, str(file_path), current_user["user_id"])
    except Exception as e:
        # Don't fail upload if AI processing fails
        print(f"AI processing failed: {e}")
    
    return PhotoResponse(**db.get_photos(current_user["user_id"], limit=1)[0])

@app.get("/api/photos", response_model=List[PhotoResponse])
async def list_photos(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    photos = db.get_photos(current_user["user_id"], limit, offset)
    return [PhotoResponse(**photo) for photo in photos]

@app.get("/api/photos/{photo_id}")
async def get_photo(
    photo_id: int,
    current_user: dict = Depends(get_current_user)
):
    photos = db.get_photos(current_user["user_id"])
    photo = next((p for p in photos if p["id"] == photo_id), None)
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    return FileResponse(
        path=photo["file_path"],
        media_type="image/jpeg"
    )

@app.get("/api/photos/{photo_id}/thumbnail")
async def get_photo_thumbnail(
    photo_id: int,
    current_user: dict = Depends(get_current_user)
):
    photos = db.get_photos(current_user["user_id"])
    photo = next((p for p in photos if p["id"] == photo_id), None)
    
    if not photo or not photo["thumbnail_path"]:
        raise HTTPException(status_code=404, detail="Photo or thumbnail not found")
    
    return FileResponse(
        path=photo["thumbnail_path"],
        media_type="image/jpeg"
    )

# AI/Person Management endpoints
@app.post("/api/people")
async def create_person(
    name: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    person_id = person_manager.create_person(current_user["user_id"], name)
    return {"id": person_id, "name": name}

@app.get("/api/people")
async def list_people(current_user: dict = Depends(get_current_user)):
    people = person_manager.get_people(current_user["user_id"])
    return people

@app.post("/api/people/{person_id}/train")
async def train_person(
    person_id: int,
    photos: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Save training photos temporarily
    temp_paths = []
    for photo in photos:
        temp_path = settings.PHOTOS_DIR / f"temp_{uuid.uuid4()}"
        content = await photo.read()
        async with aiofiles.open(temp_path, 'wb') as f:
            await f.write(content)
        temp_paths.append(str(temp_path))
    
    # Train the person
    success = person_manager.train_person(person_id, temp_paths)
    
    # Clean up temp files
    for temp_path in temp_paths:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    if success:
        return {"message": "Person trained successfully"}
    else:
        raise HTTPException(status_code=400, detail="Training failed")

@app.get("/api/people/{person_id}/photos")
async def get_photos_by_person(
    person_id: int,
    current_user: dict = Depends(get_current_user)
):
    photo_ids = person_manager.search_photos_by_person(current_user["user_id"], person_id)
    photos = db.get_photos(current_user["user_id"])
    matched_photos = [p for p in photos if p["id"] in photo_ids]
    return [PhotoResponse(**photo) for photo in matched_photos]

# Serve web interface
@app.get("/")
async def root():
    return FileResponse("web/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
