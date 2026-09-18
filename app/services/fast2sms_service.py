import logging
from typing import Dict, Any, List, Optional
import httpx

from app.core.config.settings import get_settings
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

class Fast2SMSService:
    """Service to interact with Fast2SMS API for WhatsApp messaging."""

    def __init__(self):
        settings = get_settings()
        # API Authorization token from settings
        self.api_key = settings.WHATSAPP_API_KEY
        if not self.api_key:
            logger.warning("WHATSAPP_API_KEY is not set in environment variables")
            
        self.base_url = "https://www.fast2sms.com/dev/whatsapp"
        
        # Hardcoding the static values from the curl for the template
        self.message_id = "33426"
        self.phone_number_id = "1052723054600851"

    async def send_whatsapp_template(
        self,
        mobile_number: str,
        variables: List[str],
        media_url: str,
        udf1: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a WhatsApp template message using Fast2SMS API.
        
        Args:
            mobile_number: The callee's phone number
            variables: A list of string variables to insert into the template
            media_url: The media URL for the message
            udf1: Optional custom identifier (used for call_id logging)
            
        Returns:
            The JSON response from Fast2SMS
        """
        # Fast2SMS expects numbers without the leading + or spaces
        clean_number = mobile_number.replace("+", "").replace(" ", "").strip()
        
        # If the number includes India's 91 country code (12 digits), strip it to 10 digits
        if clean_number.startswith("91") and len(clean_number) == 12:
            clean_number = clean_number[2:]
        
        # Hardcode all fields except numbers as requested
        params = {
            "message_id": "33426",
            "phone_number_id": "1052723054600851",
            "numbers": clean_number,
            "variables_values": "8056310199|https://www.enabler.studio/#apply",
            "media_url": "https://cumma-images.s3.eu-north-1.amazonaws.com/enabler_studio.png",
        }
        
        headers = {
            "Authorization": self.api_key,
            "accept": "application/json"
        }
        
        logger.info(
            "Sending WhatsApp template", 
            mobile_number=clean_number, 
            call_id=udf1
        )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=15.0
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    "WhatsApp template sent successfully", 
                    response=result, 
                    call_id=udf1
                )
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(
                "Fast2SMS API error", 
                status_code=e.response.status_code, 
                error=e.response.text,
                call_id=udf1
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to send WhatsApp template", 
                error=str(e), 
                call_id=udf1
            )
            raise
