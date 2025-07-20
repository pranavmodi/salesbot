import os
import json
import logging
import urllib.request
from typing import Dict, List, Optional

# Set up logger for the service
logger = logging.getLogger(__name__)

class PossibleMindsAnalyticsService:
    def __init__(self, base_url: str = "https://possibleminds.in"):
        """
        Initialize PossibleMinds Analytics Service.
        
        Args:
            base_url: The base URL for the analytics service endpoint.
        """
        self.base_url = base_url
        self.endpoint = f"{self.base_url}/.netlify/functions/get-campaign-clicks"
        logger.info("Initialized PossibleMindsAnalyticsService")

    def get_campaign_clicks(self, campaign_id: str) -> Dict:
        """
        Get campaign click data from the PossibleMinds endpoint.
        
        Args:
            campaign_id: The ID of the campaign to fetch data for.
            
        Returns:
            A dictionary containing the API response.
        """
        url = f"{self.endpoint}?campaign_id={campaign_id}"
        
        try:
            logger.info(f"Fetching clicks for campaign {campaign_id} from {url}")
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    logger.info(f"Successfully fetched {len(data.get('clicks', []))} clicks for campaign {campaign_id}")
                    return data
                else:
                    error_body = response.read().decode('utf-8')
                    logger.error(f"Error fetching clicks: {response.status} - {error_body}")
                    return {"success": False, "message": f"API Error: {response.status}", "details": error_body}
        except Exception as e:
            logger.error(f"An exception occurred while fetching campaign clicks: {e}")
            return {"success": False, "message": "An exception occurred", "error": str(e)}

def create_possibleminds_service() -> PossibleMindsAnalyticsService:
    """
    Factory function to create a PossibleMindsAnalyticsService instance.
    
    Returns:
        An instance of PossibleMindsAnalyticsService.
    """
    logger.info("Creating PossibleMindsAnalyticsService instance.")
    return PossibleMindsAnalyticsService()
