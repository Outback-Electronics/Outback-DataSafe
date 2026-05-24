import face_recognition
import numpy as np
import cv2
from PIL import Image, ImageDraw
from pathlib import Path
from typing import List, Tuple, Optional
import pickle
import io

class AIProcessor:
    def __init__(self):
        self.encoding_model = "hog"  # or "cnn" for better accuracy but slower
    
    def detect_faces(self, image_path: str) -> List[Tuple[Tuple[int, int, int, int], np.ndarray]]:
        """
        Detect faces in an image and return face locations and encodings.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of tuples (face_location, face_encoding)
            face_location: (top, right, bottom, left)
            face_encoding: 128-dimensional face encoding
        """
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(image, model=self.encoding_model)
            
            # Generate face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            return list(zip(face_locations, face_encodings))
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def compare_faces(self, known_encoding: np.ndarray, unknown_encoding: np.ndarray, tolerance: float = 0.6) -> bool:
        """
        Compare two face encodings to see if they match.
        
        Args:
            known_encoding: Known face encoding
            unknown_encoding: Unknown face encoding
            tolerance: How much distance to consider it a match (lower is stricter)
            
        Returns:
            True if faces match, False otherwise
        """
        try:
            matches = face_recognition.compare_faces([known_encoding], unknown_encoding, tolerance=tolerance)
            return matches[0]
        except Exception as e:
            print(f"Error comparing faces: {e}")
            return False
    
    def find_best_match(self, known_encodings: List[np.ndarray], unknown_encoding: np.ndarray, tolerance: float = 0.6) -> Optional[int]:
        """
        Find the best matching known face for an unknown encoding.
        
        Args:
            known_encodings: List of known face encodings
            unknown_encoding: Unknown face encoding
            tolerance: How much distance to consider it a match
            
        Returns:
            Index of best match or None if no match
        """
        try:
            face_distances = face_recognition.face_distance(known_encodings, unknown_encoding)
            best_match_index = np.argmin(face_distances)
            
            if face_distances[best_match_index] <= tolerance:
                return best_match_index
            return None
        except Exception as e:
            print(f"Error finding best match: {e}")
            return None
    
    def draw_faces(self, image_path: str, face_locations: List[Tuple[int, int, int, int]], output_path: str):
        """
        Draw rectangles around detected faces in an image.
        
        Args:
            image_path: Path to input image
            face_locations: List of face locations
            output_path: Path to save output image
        """
        try:
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            
            for (top, right, bottom, left) in face_locations:
                draw.rectangle([(left, top), (right, bottom)], outline="red", width=3)
            
            image.save(output_path)
        except Exception as e:
            print(f"Error drawing faces: {e}")
    
    def extract_metadata(self, image_path: str) -> dict:
        """
        Extract metadata from image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with metadata
        """
        try:
            from PIL.ExifTags import TAGS
            
            image = Image.open(image_path)
            exif_data = image._getexif()
            
            if exif_data:
                metadata = {}
                for tag, value in exif_data.items():
                    decoded = TAGS.get(tag, tag)
                    metadata[decoded] = value
                return metadata
            
            return {}
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return {}
    
    def get_image_dimensions(self, image_path: str) -> Tuple[int, int]:
        """
        Get image dimensions.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (width, height)
        """
        try:
            image = Image.open(image_path)
            return image.size
        except Exception as e:
            print(f"Error getting dimensions: {e}")
            return (0, 0)

class PersonManager:
    def __init__(self, database):
        self.database = database
        self.ai_processor = AIProcessor()
    
    def create_person(self, user_id: int, name: str) -> int:
        """Create a new person entry."""
        with self.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO people (user_id, name) VALUES (?, ?)",
                (user_id, name)
            )
            return cursor.lastrowid
    
    def get_person(self, person_id: int) -> Optional[dict]:
        """Get person by ID."""
        with self.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM people WHERE id = ?", (person_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_people(self, user_id: int) -> List[dict]:
        """Get all people for a user."""
        with self.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM people WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def process_photo_faces(self, photo_id: int, photo_path: str, user_id: int):
        """
        Process a photo to detect and identify faces.
        
        Args:
            photo_id: Photo ID in database
            photo_path: Path to photo file
            user_id: User ID
        """
        # Detect faces
        faces = self.ai_processor.detect_faces(photo_path)
        
        # Get all known people for this user
        people = self.get_people(user_id)
        known_encodings = []
        person_ids = []
        
        for person in people:
            # Get face encodings for this person from database
            with self.database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT face_encoding FROM faces WHERE person_id = ?",
                    (person['id'],)
                )
                rows = cursor.fetchall()
                for row in rows:
                    encoding = pickle.loads(row['face_encoding'])
                    known_encodings.append(encoding)
                    person_ids.append(person['id'])
        
        # Store detected faces
        for face_location, face_encoding in faces:
            # Try to match with known people
            matched_person_id = None
            if known_encodings:
                best_match = self.ai_processor.find_best_match(known_encodings, face_encoding)
                if best_match is not None:
                    matched_person_id = person_ids[best_match]
            
            # Store face in database
            with self.database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO faces (photo_id, face_encoding, face_box, person_id) 
                       VALUES (?, ?, ?, ?)""",
                    (
                        photo_id,
                        pickle.dumps(face_encoding),
                        str(face_location),
                        matched_person_id
                    )
                )
    
    def train_person(self, person_id: int, photo_paths: List[str]):
        """
        Train a person using multiple photos.
        
        Args:
            person_id: Person ID
            photo_paths: List of photo paths for training
        """
        person = self.get_person(person_id)
        if not person:
            return False
        
        # Clear existing encodings for this person
        with self.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM faces WHERE person_id = ?", (person_id,))
        
        # Process each photo
        for photo_path in photo_paths:
            faces = self.ai_processor.detect_faces(photo_path)
            
            for face_location, face_encoding in faces:
                # Store face encoding
                with self.database.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """INSERT INTO faces (photo_id, face_encoding, face_box, person_id) 
                           VALUES (?, ?, ?, ?)""",
                        (
                            None,  # photo_id can be None for training data
                            pickle.dumps(face_encoding),
                            str(face_location),
                            person_id
                        )
                    )
        
        return True
    
    def search_photos_by_person(self, user_id: int, person_id: int) -> List[int]:
        """
        Search for photos containing a specific person.
        
        Args:
            user_id: User ID
            person_id: Person ID
            
        Returns:
            List of photo IDs
        """
        with self.database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT DISTINCT photo_id FROM faces 
                   WHERE person_id = ? AND photo_id IS NOT NULL""",
                (person_id,)
            )
            rows = cursor.fetchall()
            return [row['photo_id'] for row in rows]
