# Outback DataSafe

Self-hosted Google Drive and Google Photos alternative built from scratch with Python, HTML, PySide6, and Kotlin.

## Features

- **File Storage**: Google Drive alternative with folder navigation, file upload/download, and user quotas
- **Photo Management**: Google Photos alternative with AI face recognition and smart albums
- **Multi-Platform**: Web interface, Windows/Linux desktop client, and Android app
- **User Management**: Per-user storage quotas and authentication
- **AI Features**: Face detection, person identification, and photo search by person

## Architecture

- **Backend**: Python FastAPI server with SQLite database
- **Web**: HTML/CSS/JavaScript single-page application
- **Desktop**: PySide6 Qt application for Windows/Linux
- **Mobile**: Kotlin Android app with Material Design
- **AI**: Face recognition using face-recognition library

## Quick Start

### Backend Server (Windows 11 Pro)

1. Install Python 3.9+
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python -m backend.main
```

Server will start on `http://localhost:8000`

Default admin credentials:
- Username: `admin`
- Password: `admin123`

**Important**: Change the default admin password after first login!

### Web Interface

Access at: `http://localhost:8000`

### Desktop Client (Windows/Linux)

1. Install Python 3.9+
2. Install dependencies:
```bash
cd desktop
pip install -r requirements.txt
```

3. Run the client:
```bash
python client.py
```

### Android App

1. Open the `android` directory in Android Studio
2. Update the server IP in `ApiClient.kt` (line 23)
3. Build and run on your device or emulator

## Configuration

### Backend Configuration

Edit `backend/config.py` or set environment variables to customize:

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `STORAGE_DIR`: Base storage directory
- `DEFAULT_USER_QUOTA`: Default storage quota per user (default: 100GB, set via `DEFAULT_USER_QUOTA` env var)
- `MAX_PHOTO_SIZE`: Maximum photo upload size (default: 50MB)
- `SECRET_KEY`: JWT signing key (change this in production!)

**Note:** The quota is a soft limit per user, not a requirement for physical storage. The system will work with any amount of available disk space - it just prevents users from storing more than their allocated quota.

### Storage Structure

```
storage/
├── files/          # User files
├── photos/         # Original photos
├── thumbnails/     # Photo thumbnails
data/
└── database.db     # SQLite database
```

## Usage

### Web Interface

1. **Login**: Use admin credentials or register a new account
2. **Files**: Upload files, create folders, navigate directories
3. **Photos**: Upload photos, view gallery, AI face recognition
4. **Quota**: View storage usage in sidebar

### Desktop Client

1. **Login**: Enter server URL and credentials
2. **Files Tab**: Upload files, create folders, navigate directories
3. **Photos Tab**: Upload photos, view gallery
4. **Storage**: View quota information in toolbar

### Android App

1. **Login**: Enter username and password
2. **Files Tab**: Upload files, create folders, navigate directories
3. **Photos Tab**: Upload photos, view gallery
4. **Storage**: View quota information

## AI Features

### Face Recognition

Photos are automatically processed for face detection when uploaded. To identify people:

1. Create a person via API: `POST /api/people` with `name` parameter
2. Train the person: `POST /api/people/{person_id}/train` with training photos
3. Search photos by person: `GET /api/people/{person_id}/photos`

### Training a Person

Use curl or similar:

```bash
# Create person
curl -X POST http://localhost:8000/api/people \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "name=John Doe"

# Train with photos
curl -X POST http://localhost:8000/api/people/1/train \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "photos=@photo1.jpg" \
  -F "photos=@photo2.jpg"

# Search photos
curl http://localhost:8000/api/people/1/photos \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## API Documentation

### Authentication

**Register**
```
POST /api/auth/register
Content-Type: application/json

{
  "username": "user",
  "email": "user@example.com",
  "password": "password"
}
```

**Login**
```
POST /api/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}

Response:
{
  "access_token": "token",
  "token_type": "bearer"
}
```

### Files

**List Files**
```
GET /api/files?parent_id=123
Authorization: Bearer token
```

**Upload File**
```
POST /api/files
Authorization: Bearer token
Content-Type: multipart/form-data

file: <file>
parent_id: 123 (optional)
```

**Create Folder**
```
POST /api/files/directory
Authorization: Bearer token
Content-Type: application/json

{
  "filename": "folder_name",
  "parent_id": 123,
  "is_directory": true
}
```

**Download File**
```
GET /api/files/{file_id}/download
Authorization: Bearer token
```

**Delete File**
```
DELETE /api/files/{file_id}
Authorization: Bearer token
```

### Photos

**List Photos**
```
GET /api/photos?limit=100&offset=0
Authorization: Bearer token
```

**Upload Photo**
```
POST /api/photos
Authorization: Bearer token
Content-Type: multipart/form-data

file: <image file>
```

**Get Photo**
```
GET /api/photos/{photo_id}
Authorization: Bearer token
```

**Get Thumbnail**
```
GET /api/photos/{photo_id}/thumbnail
Authorization: Bearer token
```

### People (AI)

**Create Person**
```
POST /api/people
Authorization: Bearer token
Content-Type: multipart/form-data

name: "Person Name"
```

**List People**
```
GET /api/people
Authorization: Bearer token
```

**Train Person**
```
POST /api/people/{person_id}/train
Authorization: Bearer token
Content-Type: multipart/form-data

photos: <training photos>
```

**Get Photos by Person**
```
GET /api/people/{person_id}/photos
Authorization: Bearer token
```

## Security Recommendations

1. **Change default passwords**: Update admin password immediately
2. **Use strong SECRET_KEY**: Generate a random key for JWT signing
3. **Enable HTTPS**: Use reverse proxy (nginx) with SSL for production
4. **Network isolation**: Keep server on local network initially
5. **Regular backups**: Backup `storage/` and `data/database.db` regularly
6. **Firewall**: Configure Windows Firewall to restrict access

## Backup Strategy

### Manual Backup

```bash
# Stop server
# Backup storage and database
robocopy "C:\path\to\storage" "Z:\backup\storage" /E
robocopy "C:\path\to\data" "Z:\backup\data" /E
# Restart server
```

### Database Backup

```bash
# SQLite backup
copy data\database.db backup\database.db
```

## Troubleshooting

### Server won't start

- Check Python version (3.9+ required)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check port 8000 is not in use

### Can't access from other devices

- Check Windows Firewall allows port 8000
- Verify server IP address
- Ensure both devices on same network

### Face recognition not working

- Install dlib: `pip install dlib` (may require CMake and Visual Studio)
- For Windows, precompiled binaries may be needed
- Face recognition is optional - server works without it

### Desktop client connection issues

- Verify server is running
- Check server URL in client
- Ensure network connectivity

### Android app connection issues

- Update server IP in `ApiClient.kt`
- For emulator, use `10.0.2.2` (localhost mapping)
- For real device, use computer's local IP
- Ensure device and server on same network

## Future Enhancements

- [ ] Cloudflare Tunnel integration for remote access
- [ ] End-to-end encryption
- [ ] Video support
- [ ] Advanced AI features (object detection, scene recognition)
- [ ] Sharing and collaboration features
- [ ] Mobile app background sync
- [ ] WebDAV support
- [ ] Calendar and contacts (Nextcloud-style)

## License

MIT License - Feel free to use and modify for your personal use.

## Support

For issues and questions, check the troubleshooting section or review the API documentation.
