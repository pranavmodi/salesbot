import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange,
    FilterExpression,
    Filter,
    FilterExpressionList
)
from google.oauth2 import service_account

# Set up logger for GA4 service
logger = logging.getLogger(__name__)

class GA4AnalyticsService:
    def __init__(self, credentials_file: str, property_id: str):
        """Initialize GA4 Analytics Service
        
        Args:
            credentials_file: Path to the service account JSON file
            property_id: GA4 Property ID (e.g., '496568289')
        """
        logger.info(f"Initializing GA4AnalyticsService with property_id: {property_id}")
        logger.info(f"Credentials file path: {credentials_file}")
        
        if not os.path.exists(credentials_file):
            logger.error(f"Credentials file not found: {credentials_file}")
            raise FileNotFoundError(f"GA4 credentials file not found: {credentials_file}")
        
        self.property_id = f"properties/{property_id}"
        logger.info(f"Using GA4 property: {self.property_id}")
        
        try:
            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )
            logger.info("Successfully loaded service account credentials")
            
            # Initialize the client
            self.client = BetaAnalyticsDataClient(credentials=credentials)
            logger.info("Successfully initialized GA4 client")
        except Exception as e:
            logger.error(f"Failed to initialize GA4 client: {str(e)}")
            raise
    
    def get_campaign_analytics(self, campaign_id: str, days: int = 30) -> Dict:
        """Get analytics data for a specific campaign
        
        Args:
            campaign_id: Campaign ID to filter by
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with campaign analytics data
        """
        logger.info(f"Getting campaign analytics for campaign_id: {campaign_id}, days: {days}")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Build the request
        request = RunReportRequest(
            property=self.property_id,
            dimensions=[
                Dimension(name="customEvent:company_name"),
                Dimension(name="customEvent:recipient_email"), 
                Dimension(name="customEvent:campaign_id"),
                Dimension(name="date"),
                Dimension(name="deviceCategory"),
                Dimension(name="city"),
                Dimension(name="country")
            ],
            metrics=[
                Metric(name="eventCount"),
                Metric(name="sessions"),
                Metric(name="users")
            ],
            date_ranges=[DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )],
            dimension_filter=FilterExpression(
                and_group=FilterExpressionList(
                    expressions=[
                        FilterExpression(
                            filter=Filter(
                                field_name="eventName",
                                string_filter=Filter.StringFilter(
                                    match_type=Filter.StringFilter.MatchType.EXACT,
                                    value="report_click"
                                )
                            )
                        ),
                        FilterExpression(
                            filter=Filter(
                                field_name="customEvent:campaign_id", 
                                string_filter=Filter.StringFilter(
                                    match_type=Filter.StringFilter.MatchType.EXACT,
                                    value=campaign_id
                                )
                            )
                        )
                    ]
                )
            )
        )
        
        logger.info(f"Executing GA4 request for campaign {campaign_id}")
        logger.debug(f"Request details: property={self.property_id}, date_range={start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        try:
            # Execute the request
            response = self.client.run_report(request)
            logger.info(f"GA4 request successful for campaign {campaign_id}")
            logger.debug(f"Response row count: {response.row_count}")
            
            result = self._process_campaign_response(response, campaign_id)
            logger.info(f"Processed campaign analytics: total_clicks={result.get('total_clicks', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"GA4 request failed for campaign {campaign_id}: {str(e)}")
            raise
    
    def get_all_campaigns_analytics(self, days: int = 30) -> List[Dict]:
        """Get analytics data for all campaigns
        
        Args:
            days: Number of days to look back (default: 30)
            
        Returns:
            List of dictionaries with campaign analytics data
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get report_click events grouped by campaign
        request = RunReportRequest(
            property=self.property_id,
            dimensions=[
                Dimension(name="customEvent:campaign_id"),
                Dimension(name="customEvent:company_name"),
                Dimension(name="customEvent:recipient_email")
            ],
            metrics=[
                Metric(name="eventCount"),
                Metric(name="users")
            ],
            date_ranges=[DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.EXACT,
                        value="report_click"
                    )
                )
            )
        )
        
        response = self.client.run_report(request)
        
        return self._process_all_campaigns_response(response)
    
    def get_detailed_clicks(self, campaign_id: str, days: int = 30) -> List[Dict]:
        """Get detailed click data for a specific campaign
        
        Args:
            campaign_id: Campaign ID to filter by
            days: Number of days to look back (default: 30)
            
        Returns:
            List of detailed click records
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        request = RunReportRequest(
            property=self.property_id,
            dimensions=[
                Dimension(name="customEvent:company_name"),
                Dimension(name="customEvent:recipient_email"),
                Dimension(name="customEvent:recipient_id"),
                Dimension(name="customEvent:campaign_id"),
                Dimension(name="dateHour"),
                Dimension(name="deviceCategory"),
                Dimension(name="operatingSystem"),
                Dimension(name="browser"),
                Dimension(name="city"),
                Dimension(name="country"),
                Dimension(name="source"),
                Dimension(name="medium")
            ],
            metrics=[
                Metric(name="eventCount")
            ],
            date_ranges=[DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )],
            dimension_filter=FilterExpression(
                and_group=FilterExpressionList(
                    expressions=[
                        FilterExpression(
                            filter=Filter(
                                field_name="eventName",
                                string_filter=Filter.StringFilter(
                                    match_type=Filter.StringFilter.MatchType.EXACT,
                                    value="report_click"
                                )
                            )
                        ),
                        FilterExpression(
                            filter=Filter(
                                field_name="customEvent:campaign_id",
                                string_filter=Filter.StringFilter(
                                    match_type=Filter.StringFilter.MatchType.EXACT,
                                    value=campaign_id
                                )
                            )
                        )
                    ]
                )
            )
        )
        
        response = self.client.run_report(request)
        
        return self._process_detailed_clicks_response(response)
    
    def _process_campaign_response(self, response, campaign_id: str) -> Dict:
        """Process the GA4 response for campaign analytics"""
        total_clicks = 0
        unique_companies = set()
        unique_recipients = set()
        clicks_by_date = {}
        device_breakdown = {}
        location_data = []
        
        for row in response.rows:
            company_name = row.dimension_values[0].value if row.dimension_values[0].value != "(not set)" else "Unknown"
            recipient_email = row.dimension_values[1].value if row.dimension_values[1].value != "(not set)" else "Unknown"
            date = row.dimension_values[3].value
            device = row.dimension_values[4].value
            city = row.dimension_values[5].value  
            country = row.dimension_values[6].value
            
            click_count = int(row.metric_values[0].value)
            total_clicks += click_count
            
            unique_companies.add(company_name)
            unique_recipients.add(recipient_email)
            
            # Track clicks by date
            if date not in clicks_by_date:
                clicks_by_date[date] = 0
            clicks_by_date[date] += click_count
            
            # Track device breakdown
            if device not in device_breakdown:
                device_breakdown[device] = 0
            device_breakdown[device] += click_count
            
            # Track location data
            if city != "(not set)" or country != "(not set)":
                location_data.append({
                    "city": city if city != "(not set)" else "Unknown",
                    "country": country if country != "(not set)" else "Unknown", 
                    "clicks": click_count
                })
        
        # Convert clicks_by_date to array format expected by dashboard
        clicks_by_date_array = []
        for date, clicks in clicks_by_date.items():
            clicks_by_date_array.append({
                "date": date,
                "clicks": clicks
            })
        # Sort by date descending (most recent first)
        clicks_by_date_array.sort(key=lambda x: x["date"], reverse=True)
        
        return {
            "campaign_id": campaign_id,
            "total_clicks": total_clicks,
            "unique_companies": len(unique_companies),
            "unique_recipients": len(unique_recipients),
            "clicks_by_date": clicks_by_date_array,
            "device_breakdown": device_breakdown,
            "location_data": location_data,
            "click_rate": f"{total_clicks}%" if total_clicks > 0 else "0%"
        }
    
    def _process_all_campaigns_response(self, response) -> List[Dict]:
        """Process the GA4 response for all campaigns analytics"""
        campaigns_data = {}
        
        for row in response.rows:
            campaign_id = row.dimension_values[0].value
            company_name = row.dimension_values[1].value if row.dimension_values[1].value != "(not set)" else "Unknown"
            recipient_email = row.dimension_values[2].value if row.dimension_values[2].value != "(not set)" else "Unknown"
            
            click_count = int(row.metric_values[0].value)
            users = int(row.metric_values[1].value)
            
            if campaign_id not in campaigns_data:
                campaigns_data[campaign_id] = {
                    "campaign_id": campaign_id,
                    "total_clicks": 0,
                    "unique_companies": set(),
                    "unique_recipients": set(),
                    "users": 0
                }
            
            campaigns_data[campaign_id]["total_clicks"] += click_count
            campaigns_data[campaign_id]["unique_companies"].add(company_name)
            campaigns_data[campaign_id]["unique_recipients"].add(recipient_email)
            campaigns_data[campaign_id]["users"] += users
        
        # Convert sets to counts and format the response
        result = []
        for campaign_id, data in campaigns_data.items():
            result.append({
                "campaign_id": campaign_id,
                "total_clicks": data["total_clicks"],
                "unique_companies": len(data["unique_companies"]),
                "unique_recipients": len(data["unique_recipients"]),
                "users": data["users"],
                "click_rate": f"{data['total_clicks']}%" if data["total_clicks"] > 0 else "0%"
            })
        
        return result
    
    def _process_detailed_clicks_response(self, response) -> List[Dict]:
        """Process the GA4 response for detailed clicks"""
        clicks = []
        
        for row in response.rows:
            company_name = row.dimension_values[0].value if row.dimension_values[0].value != "(not set)" else "Unknown"
            recipient_email = row.dimension_values[1].value if row.dimension_values[1].value != "(not set)" else "Unknown" 
            recipient_id = row.dimension_values[2].value if row.dimension_values[2].value != "(not set)" else None
            campaign_id = row.dimension_values[3].value
            date_hour = row.dimension_values[4].value
            device = row.dimension_values[5].value
            os = row.dimension_values[6].value
            browser = row.dimension_values[7].value
            city = row.dimension_values[8].value
            country = row.dimension_values[9].value
            source = row.dimension_values[10].value
            medium = row.dimension_values[11].value
            
            click_count = int(row.metric_values[0].value)
            
            # Parse date_hour (format: 2024011315 = 2024-01-13 15:00)
            try:
                if len(date_hour) == 10:
                    year = int(date_hour[:4])
                    month = int(date_hour[4:6])
                    day = int(date_hour[6:8])
                    hour = int(date_hour[8:10])
                    clicked_at = datetime(year, month, day, hour).isoformat()
                else:
                    clicked_at = datetime.now().isoformat()
            except:
                clicked_at = datetime.now().isoformat()
            
            for _ in range(click_count):  # Create individual records for each click
                clicks.append({
                    "id": len(clicks) + 1,  # Simple incremental ID
                    "company_name": company_name,
                    "recipient_email": recipient_email,
                    "recipient_id": recipient_id,
                    "campaign_id": int(campaign_id) if campaign_id.isdigit() else campaign_id,
                    "click_timestamp": clicked_at,  # Dashboard expects this field name
                    "clicked_at": clicked_at,  # Keep both for compatibility
                    "device_type": device if device != "(not set)" else "Unknown",  # Dashboard expects this field name
                    "device_info": f"{device} | {os} | {browser}",  # Keep detailed info too
                    "browser": browser if browser != "(not set)" else "Unknown",
                    "operating_system": os if os != "(not set)" else "Unknown",
                    "country": country if country != "(not set)" else "Unknown",  # Dashboard expects this field name
                    "city": city if city != "(not set)" else "Unknown",
                    "location": f"{city}, {country}" if city != "(not set)" and country != "(not set)" else "Unknown",
                    "utm_source": source if source != "(not set)" else None,
                    "utm_medium": medium if medium != "(not set)" else None,
                    "utm_campaign": f"campaign_{campaign_id}",
                    "tracking_id": f"ga4_{campaign_id}_{len(clicks) + 1}"  # Generate tracking ID for dashboard
                })
        
        return clicks

# Factory function to create GA4 service instance
def create_ga4_service() -> GA4AnalyticsService:
    """Create GA4 Analytics Service with default configuration"""
    logger.info("Creating GA4 service with default configuration")
    
    credentials_file = "poetic-hexagon-465803-a5-557cbe7a4d60.json"
    property_id = "496568289"  # Your GA4 property ID
    
    logger.info(f"Looking for credentials file: {os.path.abspath(credentials_file)}")
    
    if not os.path.exists(credentials_file):
        logger.error(f"GA4 credentials file not found: {os.path.abspath(credentials_file)}")
        raise FileNotFoundError(f"GA4 credentials file not found: {credentials_file}")
    
    logger.info(f"Found credentials file, creating service for property: {property_id}")
    return GA4AnalyticsService(credentials_file, property_id) 