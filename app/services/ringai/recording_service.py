"""
Service for storing and retrieving call recordings with userId-based collection
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.core.config.settings import get_settings
from app.core.utils.logger import get_logger
from app.schemas.ringai.webhooks import CallRecording

logger = get_logger(__name__)


class CallRecordingService:
    """Service for managing call recordings storage with userId indexing"""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize recording service

        Args:
            storage_path: Path to store recordings (defaults to ./data/recordings)
        """
        self.settings = get_settings()
        self.storage_path = Path(storage_path or "./data/recordings")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # UserId index file: maps userId -> [recording filenames]
        self.user_index_path = self.storage_path / "user_index.json"
        self._ensure_user_index()
        
        logger.info("CallRecordingService initialized", storage_path=str(self.storage_path))

    def _ensure_user_index(self) -> None:
        """Ensure user index file exists"""
        if not self.user_index_path.exists():
            with open(self.user_index_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _get_file_path(self, call_id: str) -> Path:
        """Get file path for a call recording"""
        return self.storage_path / f"{call_id}.json"

    def _get_filename(self, call_id: str) -> str:
        """Get just the filename (not full path)"""
        return f"{call_id}.json"

    def _add_to_user_index(self, user_id: str, filename: str) -> None:
        """Add recording filename to user's collection"""
        try:
            with open(self.user_index_path, "r", encoding="utf-8") as f:
                user_index = json.load(f)
            
            if user_id not in user_index:
                user_index[user_id] = []
            
            if filename not in user_index[user_id]:
                user_index[user_id].append(filename)
            
            with open(self.user_index_path, "w", encoding="utf-8") as f:
                json.dump(user_index, f, indent=2)
                
        except Exception as e:
            logger.warning("Failed to update user index", user_id=user_id, error=str(e))

    def _get_cloudfront_url(self, filename: str) -> Optional[str]:
        """Generate CloudFront URL for recording file"""
        if not self.settings.CLOUDFRONT_BASE_URL:
            return None
        
        base_url = self.settings.CLOUDFRONT_BASE_URL.rstrip("/")
        return f"{base_url}/recordings/{filename}"

    async def save_recording(self, recording: CallRecording) -> None:
        """
        Save call recording to storage and index by userId

        Args:
            recording: Call recording data
        """
        try:
            file_path = self._get_file_path(recording.call_id)
            filename = self._get_filename(recording.call_id)
            
            # Set filename if not already set
            if not recording.recording_filename:
                recording.recording_filename = filename
            
            # Convert to dict and handle datetime serialization
            data = recording.model_dump(exclude_none=True)
            if isinstance(data.get("created_at"), datetime):
                data["created_at"] = data["created_at"].isoformat()
            if isinstance(data.get("completed_at"), datetime):
                data["completed_at"] = data["completed_at"].isoformat()
            if isinstance(data.get("called_on"), datetime):
                data["called_on"] = data["called_on"].isoformat()

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Index by userId if provided
            if recording.user_id:
                self._add_to_user_index(recording.user_id, filename)

            logger.info(
                "Call recording saved",
                call_id=recording.call_id,
                user_id=recording.user_id,
                phone_number=recording.phone_number,
                has_transcription=bool(recording.transcription),
            )

        except Exception as e:
            logger.error("Failed to save call recording", call_id=recording.call_id, error=str(e))
            raise

    async def get_recording(self, call_id: str) -> Optional[CallRecording]:
        """
        Retrieve call recording by call ID with CloudFront URL

        Args:
            call_id: RingAI call ID

        Returns:
            Call recording if found, None otherwise
        """
        try:
            file_path = self._get_file_path(call_id)
            
            if not file_path.exists():
                logger.debug("Call recording not found", call_id=call_id)
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse datetime strings back to datetime objects
            if "created_at" in data and isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            if "completed_at" in data and isinstance(data["completed_at"], str):
                data["completed_at"] = datetime.fromisoformat(data["completed_at"])
            if "called_on" in data and isinstance(data["called_on"], str):
                try:
                    data["called_on"] = datetime.fromisoformat(data["called_on"].replace("Z", "+00:00"))
                except Exception:
                    data["called_on"] = None

            recording = CallRecording(**data)
            
            # Replace recording_url with CloudFront URL if available
            if recording.recording_filename:
                cloudfront_url = self._get_cloudfront_url(recording.recording_filename)
                if cloudfront_url:
                    recording.recording_url = cloudfront_url

            return recording

        except Exception as e:
            logger.error("Failed to retrieve call recording", call_id=call_id, error=str(e))
            return None

    async def get_recordings_by_user_id(self, user_id: str) -> List[CallRecording]:
        """
        Retrieve all recordings for a user ID

        Args:
            user_id: User ID to search for

        Returns:
            List of call recordings with CloudFront URLs
        """
        recordings = []
        
        try:
            with open(self.user_index_path, "r", encoding="utf-8") as f:
                user_index = json.load(f)
            
            filenames = user_index.get(user_id, [])
            
            for filename in filenames:
                # Extract call_id from filename (remove .json)
                call_id = filename.replace(".json", "")
                recording = await self.get_recording(call_id)
                if recording:
                    recordings.append(recording)

            logger.info(
                "Retrieved recordings by user_id",
                user_id=user_id,
                count=len(recordings),
            )

        except Exception as e:
            logger.error("Failed to retrieve recordings by user_id", user_id=user_id, error=str(e))

        return recordings

    async def get_recordings_by_phone(self, phone_number: str) -> List[CallRecording]:
        """
        Retrieve all recordings for a phone number

        Args:
            phone_number: Phone number to search for

        Returns:
            List of call recordings
        """
        recordings = []
        
        try:
            for file_path in self.storage_path.glob("*.json"):
                # Skip user_index.json
                if file_path.name == "user_index.json":
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if data.get("phone_number") == phone_number:
                        # Parse datetime strings
                        if "created_at" in data and isinstance(data["created_at"], str):
                            data["created_at"] = datetime.fromisoformat(data["created_at"])
                        if "completed_at" in data and isinstance(data["completed_at"], str):
                            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
                        if "called_on" in data and isinstance(data["called_on"], str):
                            try:
                                data["called_on"] = datetime.fromisoformat(data["called_on"].replace("Z", "+00:00"))
                            except Exception:
                                data["called_on"] = None
                        
                        recording = CallRecording(**data)
                        
                        # Add CloudFront URL if available
                        if recording.recording_filename:
                            cloudfront_url = self._get_cloudfront_url(recording.recording_filename)
                            if cloudfront_url:
                                recording.recording_url = cloudfront_url
                        
                        recordings.append(recording)
                except Exception as e:
                    logger.warning("Failed to read recording file", file=str(file_path), error=str(e))
                    continue

            logger.info(
                "Retrieved recordings by phone",
                phone_number=phone_number,
                count=len(recordings),
            )

        except Exception as e:
            logger.error("Failed to retrieve recordings by phone", phone_number=phone_number, error=str(e))

        return recordings

    async def list_recordings(self, limit: int = 100) -> List[CallRecording]:
        """
        List recent call recordings

        Args:
            limit: Maximum number of recordings to return

        Returns:
            List of call recordings (sorted by created_at, newest first)
        """
        recordings = []
        
        try:
            for file_path in sorted(self.storage_path.glob("*.json"), key=os.path.getmtime, reverse=True):
                # Skip user_index.json
                if file_path.name == "user_index.json":
                    continue
                    
                if len(recordings) >= limit:
                    break
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Parse datetime strings
                    if "created_at" in data and isinstance(data["created_at"], str):
                        data["created_at"] = datetime.fromisoformat(data["created_at"])
                    if "completed_at" in data and isinstance(data["completed_at"], str):
                        data["completed_at"] = datetime.fromisoformat(data["completed_at"])
                    if "called_on" in data and isinstance(data["called_on"], str):
                        try:
                            data["called_on"] = datetime.fromisoformat(data["called_on"].replace("Z", "+00:00"))
                        except Exception:
                            data["called_on"] = None
                    
                    recording = CallRecording(**data)
                    
                    # Add CloudFront URL if available
                    if recording.recording_filename:
                        cloudfront_url = self._get_cloudfront_url(recording.recording_filename)
                        if cloudfront_url:
                            recording.recording_url = cloudfront_url
                    
                    recordings.append(recording)
                except Exception as e:
                    logger.warning("Failed to read recording file", file=str(file_path), error=str(e))
                    continue

            # Sort by created_at (newest first)
            recordings.sort(key=lambda x: x.created_at, reverse=True)

        except Exception as e:
            logger.error("Failed to list recordings", error=str(e))

        return recordings
