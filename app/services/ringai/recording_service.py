"""
Service for storing and retrieving call recordings
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.core.utils.logger import get_logger
from app.schemas.ringai.webhooks import CallRecording

logger = get_logger(__name__)


class CallRecordingService:
    """Service for managing call recordings storage"""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize recording service

        Args:
            storage_path: Path to store recordings (defaults to ./data/recordings)
        """
        self.storage_path = Path(storage_path or "./data/recordings")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info("CallRecordingService initialized", storage_path=str(self.storage_path))

    def _get_file_path(self, call_id: str) -> Path:
        """Get file path for a call recording"""
        return self.storage_path / f"{call_id}.json"

    async def save_recording(self, recording: CallRecording) -> None:
        """
        Save call recording to storage

        Args:
            recording: Call recording data
        """
        try:
            file_path = self._get_file_path(recording.call_id)
            
            # Convert to dict and handle datetime serialization
            data = recording.model_dump()
            if isinstance(data.get("created_at"), datetime):
                data["created_at"] = data["created_at"].isoformat()
            if isinstance(data.get("completed_at"), datetime):
                data["completed_at"] = data["completed_at"].isoformat()

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(
                "Call recording saved",
                call_id=recording.call_id,
                phone_number=recording.phone_number,
                has_transcription=bool(recording.transcription),
            )

        except Exception as e:
            logger.error("Failed to save call recording", call_id=recording.call_id, error=str(e))
            raise

    async def get_recording(self, call_id: str) -> Optional[CallRecording]:
        """
        Retrieve call recording by call ID

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

            return CallRecording(**data)

        except Exception as e:
            logger.error("Failed to retrieve call recording", call_id=call_id, error=str(e))
            return None

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
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if data.get("phone_number") == phone_number:
                        # Parse datetime strings
                        if "created_at" in data and isinstance(data["created_at"], str):
                            data["created_at"] = datetime.fromisoformat(data["created_at"])
                        if "completed_at" in data and isinstance(data["completed_at"], str):
                            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
                        
                        recordings.append(CallRecording(**data))
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
                    
                    recordings.append(CallRecording(**data))
                except Exception as e:
                    logger.warning("Failed to read recording file", file=str(file_path), error=str(e))
                    continue

            # Sort by created_at (newest first)
            recordings.sort(key=lambda x: x.created_at, reverse=True)

        except Exception as e:
            logger.error("Failed to list recordings", error=str(e))

        return recordings

