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
import traceback

# Set up logger for GA4 service
logger = logging.getLogger(__name__)

class GA4AnalyticsService:
    def __init__(self, credentials_file: str, property_id: str):
        """Initialize GA4 Analytics Service
        
        Args:
            credentials_file: Path to the service account JSON file
            property_id: GA4 Property ID (e.g., '496568289')
        """
        logger.info(f"=== GA4 INIT === Initializing GA4AnalyticsService with property_id: {property_id}")
        logger.info(f"=== GA4 INIT === Credentials file path: {credentials_file}")
        logger.info(f"=== GA4 INIT === Absolute credentials path: {os.path.abspath(credentials_file)}")
        
        if not os.path.exists(credentials_file):
            logger.error(f"=== GA4 INIT === Credentials file not found: {credentials_file}")
            raise FileNotFoundError(f"GA4 credentials file not found: {credentials_file}")
        
        # Check file permissions and size
        file_stats = os.stat(credentials_file)
        logger.info(f"=== GA4 INIT === Credentials file size: {file_stats.st_size} bytes")
        logger.info(f"=== GA4 INIT === Credentials file permissions: {oct(file_stats.st_mode)}")
        
        self.property_id = f"properties/{property_id}"
        logger.info(f"=== GA4 INIT === Using GA4 property: {self.property_id}")
        
        try:
            # Load and validate service account credentials
            logger.info("=== GA4 INIT === Loading service account credentials...")
            with open(credentials_file, 'r') as f:
                cred_data = json.load(f)
                logger.info(f"=== GA4 INIT === Credentials file loaded, type: {cred_data.get('type', 'unknown')}")
                logger.info(f"=== GA4 INIT === Project ID: {cred_data.get('project_id', 'unknown')}")
                logger.info(f"=== GA4 INIT === Client email: {cred_data.get('client_email', 'unknown')}")
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )
            logger.info("=== GA4 INIT === Successfully loaded service account credentials")
            logger.info(f"=== GA4 INIT === Service account email: {credentials.service_account_email}")
            
            # Initialize the client
            logger.info("=== GA4 INIT === Initializing GA4 client...")
            self.client = BetaAnalyticsDataClient(credentials=credentials)
            logger.info("=== GA4 INIT === Successfully initialized GA4 client")
            
            # Test client connection with a simple metadata request
            logger.info("=== GA4 INIT === Testing client connection...")
            try:
                # Try to get property metadata to validate access
                from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
                admin_client = AnalyticsAdminServiceClient(credentials=credentials)
                logger.info(f"=== GA4 INIT === Admin client created, testing property access...")
                logger.info(f"=== GA4 INIT === Property ID for test: {self.property_id}")
                # Don't actually call it here, just log that we could create the client
                logger.info("=== GA4 INIT === Client connection test passed")
            except Exception as test_e:
                logger.warning(f"=== GA4 INIT === Client connection test failed (non-critical): {str(test_e)}")
                
        except json.JSONDecodeError as e:
            logger.error(f"=== GA4 INIT === Invalid JSON in credentials file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"=== GA4 INIT === Failed to initialize GA4 client: {str(e)}")
            logger.error(f"=== GA4 INIT === Exception type: {type(e).__name__}")
            logger.error(f"=== GA4 INIT === Traceback: {traceback.format_exc()}")
            raise
    
    def get_campaign_analytics(self, campaign_id: str, days: int = 30) -> Dict:
        """Get analytics data for a specific campaign using only valid GA4 dimensions
        
        Args:
            campaign_id: Campaign ID to filter by
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with campaign analytics data
        """
        logger.info(f"=== GA4 REQUEST === Getting campaign analytics for campaign_id: {campaign_id}, days: {days}")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        logger.info(f"=== GA4 REQUEST === Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Use COMPATIBLE GA4 dimensions and metrics only
        logger.info("=== GA4 REQUEST === Building request with compatible GA4 dimensions and metrics...")
        
        dimensions = [
            Dimension(name="eventName"),           # Core dimension
            Dimension(name="date")                 # Basic time dimension - most compatible
        ]
        
        metrics = [
            Metric(name="eventCount")              # Core metric - compatible with eventName + date
        ]
        
        logger.info(f"=== GA4 REQUEST === Compatible dimensions: {[d.name for d in dimensions]}")
        logger.info(f"=== GA4 REQUEST === Compatible metrics: {[m.name for m in metrics]}")
        
        # Build request with compatible dimensions - filter by eventName only (no campaign filter)
        request = RunReportRequest(
            property=self.property_id,
            dimensions=dimensions,
            metrics=metrics,
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
        
        logger.info(f"=== GA4 REQUEST === Executing GA4 request for report_click events")
        logger.info(f"=== GA4 REQUEST === Property: {self.property_id}")
        logger.info(f"=== GA4 REQUEST === Filter: eventName=report_click (campaign filtering not available)")
        
        try:
            # Execute the request
            logger.info("=== GA4 REQUEST === Calling client.run_report()...")
            response = self.client.run_report(request)
            logger.info(f"=== GA4 RESPONSE === Request successful")
            logger.info(f"=== GA4 RESPONSE === Row count: {response.row_count}")
            logger.info(f"=== GA4 RESPONSE === Total rows: {len(response.rows) if response.rows else 0}")
            
            # Log response metadata
            if hasattr(response, 'metadata') and response.metadata:
                logger.info(f"=== GA4 RESPONSE === Currency code: {getattr(response.metadata, 'currency_code', 'N/A')}")
                logger.info(f"=== GA4 RESPONSE === Time zone: {getattr(response.metadata, 'time_zone', 'N/A')}")
            
            # Log dimension and metric headers for validation
            if response.dimension_headers:
                logger.info(f"=== GA4 RESPONSE === Dimension headers: {[h.name for h in response.dimension_headers]}")
            if response.metric_headers:
                logger.info(f"=== GA4 RESPONSE === Metric headers: {[h.name for h in response.metric_headers]}")
            
            # Log a sample of the first few rows for debugging
            if response.rows:
                logger.info(f"=== GA4 RESPONSE === Sample data (first 3 rows):")
                for i, row in enumerate(response.rows[:3]):
                    dim_values = [dv.value for dv in row.dimension_values]
                    metric_values = [mv.value for mv in row.metric_values]
                    logger.info(f"=== GA4 RESPONSE === Row {i+1}: dims={dim_values}, metrics={metric_values}")
            else:
                logger.info("=== GA4 RESPONSE === No data rows returned")
            
            result = self._process_valid_response(response, campaign_id)
            logger.info(f"=== GA4 RESULT === Processed analytics: total_clicks={result.get('total_clicks', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"=== GA4 ERROR === Request failed")
            logger.error(f"=== GA4 ERROR === Exception type: {type(e).__name__}")
            logger.error(f"=== GA4 ERROR === Exception message: {str(e)}")
            logger.error(f"=== GA4 ERROR === Full traceback: {traceback.format_exc()}")
            
            # Log additional context for specific error types
            if hasattr(e, 'code'):
                try:
                    logger.error(f"=== GA4 ERROR === gRPC status code: {e.code}")
                except:
                    logger.error(f"=== GA4 ERROR === gRPC status code: {getattr(e, 'code', 'unknown')}")
            if hasattr(e, 'details'):
                try:
                    logger.error(f"=== GA4 ERROR === gRPC details: {e.details}")
                except:
                    logger.error(f"=== GA4 ERROR === gRPC details: {getattr(e, 'details', 'unknown')}")
            
            raise

    def _process_valid_response(self, response, campaign_id: str) -> Dict:
        """Process GA4 response using compatible dimensions and metrics"""
        total_clicks = 0
        clicks_by_date = {}
        
        logger.info("=== GA4 PROCESSING === Processing response with compatible dimensions")
        
        for row in response.rows:
            # Compatible dimension order: eventName, date
            event_name = row.dimension_values[0].value
            date = row.dimension_values[1].value
            
            # Metrics: eventCount only
            click_count = int(row.metric_values[0].value)
            
            if event_name == "report_click":
                total_clicks += click_count
                
                # Track clicks by date
                if date not in clicks_by_date:
                    clicks_by_date[date] = 0
                clicks_by_date[date] += click_count
        
        # Convert clicks_by_date to array format
        clicks_by_date_array = []
        for date, clicks in clicks_by_date.items():
            clicks_by_date_array.append({
                "date": date,
                "clicks": clicks
            })
        clicks_by_date_array.sort(key=lambda x: x["date"], reverse=True)
        
        logger.info(f"=== GA4 PROCESSING === Processed {total_clicks} total clicks across {len(clicks_by_date)} dates")
        
        return {
            "campaign_id": campaign_id,
            "total_clicks": total_clicks,
            "unique_companies": 0,  # Not available without custom dimensions
            "unique_recipients": 0,  # Not available without custom dimensions  
            "active_users": 0,  # Not requested to maintain compatibility
            "clicks_by_date": clicks_by_date_array,
            "device_breakdown": {},  # Not available in simplified request
            "location_data": [],  # Not available in simplified request
            "click_rate": f"{total_clicks}%" if total_clicks > 0 else "0%"
        }
    
    def get_all_campaigns_analytics(self, days: int = 30) -> List[Dict]:
        """Get analytics data for all campaigns using only valid GA4 dimensions
        
        Args:
            days: Number of days to look back (default: 30)
            
        Returns:
            List of dictionaries with campaign analytics data
        """
        logger.info(f"=== GA4 ALL CAMPAIGNS === Getting all campaigns analytics for {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Use compatible GA4 dimensions and metrics only
        request = RunReportRequest(
            property=self.property_id,
            dimensions=[
                Dimension(name="eventName"),      # Core dimension
                Dimension(name="date")            # Compatible with eventCount
            ],
            metrics=[
                Metric(name="eventCount")         # Core metric - guaranteed compatible
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
        
        logger.info("=== GA4 ALL CAMPAIGNS === Executing request for all report_click events")
        
        try:
            response = self.client.run_report(request)
            logger.info(f"=== GA4 ALL CAMPAIGNS === Response received with {response.row_count} rows")
            return self._process_all_campaigns_valid_response(response)
        except Exception as e:
            logger.error(f"=== GA4 ALL CAMPAIGNS === Request failed: {str(e)}")
            raise
    
    def get_detailed_clicks(self, campaign_id: str, days: int = 30) -> List[Dict]:
        """Get detailed click data using only valid GA4 dimensions
        
        Args:
            campaign_id: Campaign ID (for logging only - GA4 can't filter by campaign without custom dimensions)
            days: Number of days to look back (default: 30)
            
        Returns:
            List of detailed click records
        """
        logger.info(f"=== GA4 DETAILED === Getting detailed clicks for campaign {campaign_id}, {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Use compatible GA4 dimensions and metrics only
        request = RunReportRequest(
            property=self.property_id,
            dimensions=[
                Dimension(name="eventName"),           # Core dimension
                Dimension(name="dateHour")             # Compatible time dimension
            ],
            metrics=[
                Metric(name="eventCount")              # Core metric - guaranteed compatible
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
        
        logger.info("=== GA4 DETAILED === Executing request for detailed clicks")
        
        try:
            response = self.client.run_report(request)
            logger.info(f"=== GA4 DETAILED === Response received with {response.row_count} rows")
            return self._process_detailed_clicks_valid_response(response)
        except Exception as e:
            logger.error(f"=== GA4 DETAILED === Request failed: {str(e)}")
            raise
    
    def _process_all_campaigns_valid_response(self, response) -> List[Dict]:
        """Process GA4 response for all campaigns using compatible dimensions only"""
        logger.info("=== GA4 ALL CAMPAIGNS === Processing response with compatible dimensions")
        
        # Simple aggregation with compatible dimensions
        total_clicks = 0
        dates_with_clicks = set()
        
        for row in response.rows:
            # Compatible dimension order: eventName, date
            event_name = row.dimension_values[0].value
            date = row.dimension_values[1].value
            
            # Metrics: eventCount only
            click_count = int(row.metric_values[0].value)
            
            if event_name == "report_click":
                total_clicks += click_count
                dates_with_clicks.add(date)
        
        logger.info(f"=== GA4 ALL CAMPAIGNS === Found {total_clicks} total clicks across all campaigns")
        
        # Return a single aggregated result since we can't separate by campaigns
        return [{
            "campaign_id": "all_campaigns",
            "campaign_name": "All Campaigns (GA4 Aggregated)",
            "total_clicks": total_clicks,
            "unique_companies": 0,  # Not available without custom dimensions
            "unique_recipients": 0,  # Not available without custom dimensions
            "active_users": 0,  # Not requested to maintain compatibility
            "click_rate": f"{total_clicks}%" if total_clicks > 0 else "0%",
            "active_dates": len(dates_with_clicks)
        }]
    
    def _process_detailed_clicks_valid_response(self, response) -> List[Dict]:
        """Process GA4 response for detailed clicks using compatible dimensions only"""
        logger.info("=== GA4 DETAILED === Processing detailed clicks with compatible dimensions")
        
        clicks = []
        
        for row in response.rows:
            # Compatible dimension order: eventName, dateHour
            event_name = row.dimension_values[0].value
            date_hour = row.dimension_values[1].value
            
            # Metrics: eventCount only
            click_count = int(row.metric_values[0].value)
            
            if event_name == "report_click":
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
                        "company_name": "Unknown",  # Not available without custom dimensions
                        "recipient_email": "Unknown",  # Not available without custom dimensions
                        "recipient_id": None,  # Not available without custom dimensions
                        "campaign_id": "unknown",  # Not available without custom dimensions
                        "click_timestamp": clicked_at,  # Dashboard expects this field name
                        "clicked_at": clicked_at,  # Keep both for compatibility
                        "device_type": "Unknown",  # Not available in simplified request
                        "device_info": "Unknown",  # Not available in simplified request
                        "browser": "Unknown",  # Not available in simplified request
                        "operating_system": "Unknown",  # Not available in simplified request
                        "country": "Unknown",  # Not available in simplified request
                        "city": "Unknown",  # Not available in simplified request
                        "location": "Unknown",  # Not available in simplified request
                        "utm_source": None,  # Not available in simplified request
                        "utm_medium": None,  # Not available in simplified request
                        "utm_campaign": "unknown",  # Not available without custom dimensions
                        "tracking_id": f"ga4_unknown_{len(clicks) + 1}"  # Generate tracking ID for dashboard
                    })
        
        logger.info(f"=== GA4 DETAILED === Processed {len(clicks)} detailed click records")
        return clicks

# Factory function to create GA4 service instance
def create_ga4_service() -> GA4AnalyticsService:
    """Create GA4 Analytics Service with default configuration"""
    logger.info("=== GA4 FACTORY === Creating GA4 service with default configuration")
    
    credentials_file = "poetic-hexagon-465803-a5-557cbe7a4d60.json"
    property_id = "496568289"  # Your GA4 property ID
    
    logger.info(f"=== GA4 FACTORY === Using credentials file: {credentials_file}")
    logger.info(f"=== GA4 FACTORY === Using property ID: {property_id}")
    logger.info(f"=== GA4 FACTORY === Looking for credentials file: {os.path.abspath(credentials_file)}")
    
    if not os.path.exists(credentials_file):
        logger.error(f"=== GA4 FACTORY === GA4 credentials file not found: {os.path.abspath(credentials_file)}")
        raise FileNotFoundError(f"GA4 credentials file not found: {credentials_file}")
    
    logger.info(f"=== GA4 FACTORY === Found credentials file, creating service for property: {property_id}")
    
    try:
        service = GA4AnalyticsService(credentials_file, property_id)
        logger.info("=== GA4 FACTORY === Successfully created GA4 service")
        return service
    except Exception as e:
        logger.error(f"=== GA4 FACTORY === Failed to create GA4 service: {str(e)}")
        logger.error(f"=== GA4 FACTORY === Exception type: {type(e).__name__}")
        logger.error(f"=== GA4 FACTORY === Traceback: {traceback.format_exc()}")
        raise