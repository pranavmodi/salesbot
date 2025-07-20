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
        """Initialize GA4 Analytics Service with Custom Parameters focus
        
        Args:
            credentials_file: Path to the service account JSON file
            property_id: GA4 Property ID
        """
        logger.info("=== GA4 CUSTOM PARAMS === Initializing GA4 service with custom parameters focus")
        self.property_id = property_id
        self.property_path = f"properties/{property_id}"
        
        try:
            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/analytics.readonly']
            )
            
            # Initialize the client
            self.client = BetaAnalyticsDataClient(credentials=credentials)
            logger.info("=== GA4 CUSTOM PARAMS === Successfully initialized GA4 client with custom parameters focus")
            
        except Exception as e:
            logger.error(f"=== GA4 CUSTOM PARAMS === Failed to initialize GA4 client: {str(e)}")
            logger.error(f"=== GA4 CUSTOM PARAMS === Traceback: {traceback.format_exc()}")
            raise

    def get_campaign_analytics(self, campaign_id: str, days: int = 30) -> Dict:
        """Get analytics data using custom event parameters from possibleminds.in
        
        Args:
            campaign_id: Campaign ID to filter by
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with campaign analytics data from custom parameters
        """
        logger.info(f"=== GA4 CUSTOM PARAMS === Getting analytics with custom parameters for campaign_id: {campaign_id}, days: {days}")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        logger.info(f"=== GA4 CUSTOM PARAMS === Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        try:
            # Query for custom dimensions that were just created in GA4
            logger.info("=== GA4 CUSTOM PARAMS === Building request with GA4 custom dimensions...")
            
            # Build the request with only confirmed working custom dimensions
            request = RunReportRequest(
                property=self.property_path,
                dimensions=[
                    Dimension(name="eventName"),
                    Dimension(name="date"),
                    Dimension(name="customEvent:custom_company_name"),      # GA4 confirmed this works
                    Dimension(name="customEvent:custom_recipient_id"),       # GA4 suggested this works
                    Dimension(name="customEvent:custom_campaign_id")        # This should work based on our custom dimension setup
                ],
                metrics=[
                    Metric(name="eventCount"),
                    Metric(name="activeUsers")
                ],
                date_ranges=[DateRange(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )],
                dimension_filter=FilterExpression(
                    and_group=FilterExpressionList(
                        expressions=[
                            FilterExpression(
                                filter=Filter(
                                    field_name="eventName",
                                    string_filter=Filter.StringFilter(value="report_click")
                                )
                            ),
                            FilterExpression(
                                filter=Filter(
                                    field_name="customEvent:custom_campaign_id",
                                    string_filter=Filter.StringFilter(value=str(campaign_id))
                                )
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"=== GA4 CUSTOM PARAMS === Executing custom dimensions request for report_click events")
            logger.info(f"=== GA4 CUSTOM PARAMS === Property: {self.property_path}")
            logger.info(f"=== GA4 CUSTOM PARAMS === Filter: eventName='report_click' AND campaign_id='{campaign_id}'")
            
            # Execute the request
            response = self.client.run_report(request)
            logger.info(f"=== GA4 CUSTOM PARAMS === Response received with {len(response.rows)} rows")
            
            # Process the response
            analytics_data = self._process_custom_analytics_response(response, campaign_id)
            logger.info(f"=== GA4 CUSTOM PARAMS === Processed analytics data: {analytics_data}")
            
            return analytics_data
            
        except Exception as e:
            logger.error(f"=== GA4 CUSTOM PARAMS === Error getting analytics: {str(e)}")
            logger.error(f"=== GA4 CUSTOM PARAMS === Traceback: {traceback.format_exc()}")
            
            # Return basic structure with error info
            return {
                'total_clicks': 0,
                'unique_users': 0,
                'data_source': 'ga4_custom_params_error',
                'error': str(e),
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }

    def get_detailed_clicks(self, campaign_id: str, days: int = 30) -> List[Dict]:
        """Get detailed click tracking data using custom event parameters from possibleminds.in
        
        Args:
            campaign_id: Campaign ID to filter by
            days: Number of days to look back (default: 30)
            
        Returns:
            List of dictionaries with detailed click data from custom parameters
        """
        logger.info(f"=== GA4 CUSTOM PARAMS CLICKS === Getting detailed clicks with custom parameters for campaign {campaign_id}, {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            logger.info("=== GA4 CUSTOM PARAMS CLICKS === Executing custom dimensions request for detailed clicks")
            
            # Build the request for detailed custom dimensions - only confirmed working ones
            request = RunReportRequest(
                property=self.property_path,
                dimensions=[
                    Dimension(name="eventName"),
                    Dimension(name="dateHour"),  # More precise timing
                    Dimension(name="customEvent:custom_company_name"),      # GA4 confirmed this works
                    Dimension(name="customEvent:custom_recipient_id"),       # GA4 suggested this works
                    Dimension(name="customEvent:custom_campaign_id"),        # This should work based on our custom dimension setup
                    Dimension(name="customEvent:visitor_ip"),
                    Dimension(name="customEvent:referrer"),
                    Dimension(name="deviceCategory")      # This is a standard dimension that should work
                ],
                metrics=[
                    Metric(name="eventCount")
                ],
                date_ranges=[DateRange(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )],
                dimension_filter=FilterExpression(
                    and_group=FilterExpressionList(
                        expressions=[
                            FilterExpression(
                                filter=Filter(
                                    field_name="eventName",
                                    string_filter=Filter.StringFilter(value="report_click")
                                )
                            ),
                            FilterExpression(
                                filter=Filter(
                                    field_name="customEvent:custom_campaign_id",
                                    string_filter=Filter.StringFilter(value=str(campaign_id))
                                )
                            )
                        ]
                    )
                ),
                limit=1000  # Get up to 1000 detailed records
            )
            
            # Execute the request
            response = self.client.run_report(request)
            logger.info(f"=== GA4 CUSTOM PARAMS CLICKS === Response received with {len(response.rows)} rows")
            
            # Process the detailed response
            detailed_clicks = self._process_custom_clicks_response(response)
            logger.info(f"=== GA4 CUSTOM PARAMS CLICKS === Processed {len(detailed_clicks)} detailed click records")
            
            return detailed_clicks
            
        except Exception as e:
            logger.error(f"=== GA4 CUSTOM PARAMS CLICKS === Error getting detailed clicks: {str(e)}")
            logger.error(f"=== GA4 CUSTOM PARAMS CLICKS === Traceback: {traceback.format_exc()}")
            return []

    def test_ga4_custom_dimensions_no_filter(self, days: int = 30) -> Dict:
        """Test GA4 custom dimensions without campaign filtering to see if we get any data"""
        logger.info(f"=== GA4 DIAGNOSTIC === Testing custom dimensions without campaign filter for {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Test request with NO campaign filtering - just get any report_click events
            request = RunReportRequest(
                property=self.property_path,
                dimensions=[
                    Dimension(name="eventName"),
                    Dimension(name="date"),
                    Dimension(name="customEvent:custom_company_name"),
                    Dimension(name="customEvent:custom_recipient_id"),
                    Dimension(name="customEvent:custom_campaign_id")
                ],
                metrics=[
                    Metric(name="eventCount"),
                    Metric(name="activeUsers")
                ],
                date_ranges=[DateRange(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(value="report_click")
                    )
                ),
                limit=100
            )
            
            logger.info(f"=== GA4 DIAGNOSTIC === Executing test request for ANY report_click events")
            response = self.client.run_report(request)
            logger.info(f"=== GA4 DIAGNOSTIC === Response received with {len(response.rows)} rows")
            
            # Process and log all data we find
            all_campaign_ids = set()
            all_companies = set()
            all_recipients = set()
            total_clicks = 0
            
            for row in response.rows:
                dims = [dim.value for dim in row.dimension_values]
                metrics = [metric.value for metric in row.metric_values]
                
                logger.info(f"=== GA4 DIAGNOSTIC === Row: dims={dims}, metrics={metrics}")
                
                if len(dims) >= 5:
                    event_name = dims[0]
                    date = dims[1]
                    company_name = dims[2]
                    recipient_id = dims[3]
                    campaign_id_from_event = dims[4]
                    
                    event_count = int(metrics[0]) if len(metrics) > 0 and metrics[0].isdigit() else 0
                    total_clicks += event_count
                    
                    if campaign_id_from_event and campaign_id_from_event != "(not set)":
                        all_campaign_ids.add(campaign_id_from_event)
                    if company_name and company_name != "(not set)":
                        all_companies.add(company_name)
                    if recipient_id and recipient_id != "(not set)":
                        all_recipients.add(recipient_id)
            
            diagnostic_data = {
                'total_rows': len(response.rows),
                'total_clicks': total_clicks,
                'unique_campaign_ids': list(all_campaign_ids),
                'unique_companies': list(all_companies),
                'unique_recipients': list(all_recipients),
                'data_source': 'ga4_diagnostic_no_filter'
            }
            
            logger.info(f"=== GA4 DIAGNOSTIC === Found {len(all_campaign_ids)} campaigns: {list(all_campaign_ids)}")
            logger.info(f"=== GA4 DIAGNOSTIC === Found {len(all_companies)} companies: {list(all_companies)}")
            logger.info(f"=== GA4 DIAGNOSTIC === Found {len(all_recipients)} recipients: {list(all_recipients)}")
            
            return diagnostic_data
            
        except Exception as e:
            logger.error(f"=== GA4 DIAGNOSTIC === Error: {str(e)}")
            return {
                'total_rows': 0,
                'total_clicks': 0,
                'unique_campaign_ids': [],
                'unique_companies': [],
                'unique_recipients': [],
                'error': str(e),
                'data_source': 'ga4_diagnostic_error'
            }

    def test_ga4_custom_dimensions_raw_data(self, days: int = 30) -> Dict:
        """Test GA4 custom dimensions and show ALL raw data including (not set) values"""
        logger.info(f"=== GA4 RAW DIAGNOSTIC === Testing custom dimensions with raw data for {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Test request to see ALL raw data
            request = RunReportRequest(
                property=self.property_path,
                dimensions=[
                    Dimension(name="eventName"),
                    Dimension(name="date"),
                    Dimension(name="customEvent:custom_company_name"),
                    Dimension(name="customEvent:custom_recipient_id"),
                    Dimension(name="customEvent:custom_campaign_id")
                ],
                metrics=[
                    Metric(name="eventCount"),
                    Metric(name="activeUsers")
                ],
                date_ranges=[DateRange(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(value="report_click")
                    )
                ),
                limit=100
            )
            
            logger.info(f"=== GA4 RAW DIAGNOSTIC === Executing raw data request")
            response = self.client.run_report(request)
            logger.info(f"=== GA4 RAW DIAGNOSTIC === Response received with {len(response.rows)} rows")
            
            # Collect ALL raw data including (not set) values
            raw_rows = []
            total_clicks = 0
            
            for i, row in enumerate(response.rows):
                dims = [dim.value for dim in row.dimension_values]
                metrics = [metric.value for metric in row.metric_values]
                
                logger.info(f"=== GA4 RAW DIAGNOSTIC === Raw Row {i+1}: dims={dims}, metrics={metrics}")
                
                event_count = int(metrics[0]) if len(metrics) > 0 and metrics[0].isdigit() else 0
                total_clicks += event_count
                
                raw_row = {
                    'row_number': i + 1,
                    'event_name': dims[0] if len(dims) > 0 else 'unknown',
                    'date': dims[1] if len(dims) > 1 else 'unknown',
                    'company_name_raw': dims[2] if len(dims) > 2 else 'unknown',
                    'recipient_id_raw': dims[3] if len(dims) > 3 else 'unknown', 
                    'campaign_id_raw': dims[4] if len(dims) > 4 else 'unknown',
                    'event_count': event_count,
                    'active_users': int(metrics[1]) if len(metrics) > 1 and metrics[1].isdigit() else 0,
                    'company_name_is_set': dims[2] != "(not set)" if len(dims) > 2 else False,
                    'recipient_id_is_set': dims[3] != "(not set)" if len(dims) > 3 else False,
                    'campaign_id_is_set': dims[4] != "(not set)" if len(dims) > 4 else False
                }
                raw_rows.append(raw_row)
            
            diagnostic_data = {
                'total_rows': len(response.rows),
                'total_clicks': total_clicks,
                'raw_data': raw_rows,
                'summary': {
                    'any_company_names_set': any(row['company_name_is_set'] for row in raw_rows),
                    'any_recipient_ids_set': any(row['recipient_id_is_set'] for row in raw_rows),
                    'any_campaign_ids_set': any(row['campaign_id_is_set'] for row in raw_rows),
                    'all_company_names': list(set(row['company_name_raw'] for row in raw_rows)),
                    'all_recipient_ids': list(set(row['recipient_id_raw'] for row in raw_rows)),
                    'all_campaign_ids': list(set(row['campaign_id_raw'] for row in raw_rows))
                },
                'data_source': 'ga4_raw_diagnostic'
            }
            
            logger.info(f"=== GA4 RAW DIAGNOSTIC === Summary:")
            logger.info(f"   Company names set: {diagnostic_data['summary']['any_company_names_set']}")
            logger.info(f"   Recipient IDs set: {diagnostic_data['summary']['any_recipient_ids_set']}")
            logger.info(f"   Campaign IDs set: {diagnostic_data['summary']['any_campaign_ids_set']}")
            logger.info(f"   All company values: {diagnostic_data['summary']['all_company_names']}")
            logger.info(f"   All recipient values: {diagnostic_data['summary']['all_recipient_ids']}")
            logger.info(f"   All campaign values: {diagnostic_data['summary']['all_campaign_ids']}")
            
            return diagnostic_data
            
        except Exception as e:
            logger.error(f"=== GA4 RAW DIAGNOSTIC === Error: {str(e)}")
            return {
                'total_rows': 0,
                'total_clicks': 0,
                'raw_data': [],
                'error': str(e),
                'data_source': 'ga4_raw_diagnostic_error'
            }

    def _process_custom_analytics_response(self, response, campaign_id: str) -> Dict:
        """Process GA4 response with confirmed working custom dimensions for analytics data"""
        logger.info("=== GA4 CUSTOM PARAMS === Processing analytics response with confirmed custom dimensions")
        
        total_clicks = 0
        unique_users = 0
        companies = set()
        recipients = set()
        
        for row in response.rows:
            # Extract data from confirmed custom dimensions only
            dims = [dim.value for dim in row.dimension_values]
            metrics = [metric.value for metric in row.metric_values]
            
            logger.info(f"=== GA4 CUSTOM PARAMS === Row data: dims={dims}, metrics={metrics}")
            
            # dims = [eventName, date, company_name, recipient_id, campaign_id]
            # metrics = [eventCount, activeUsers]
            
            if len(dims) >= 5 and len(metrics) >= 2:
                event_name = dims[0]
                date = dims[1]
                company_name = dims[2]
                recipient_id = dims[3]
                campaign_id_from_event = dims[4]
                
                event_count = int(metrics[0]) if metrics[0].isdigit() else 0
                active_users = int(metrics[1]) if metrics[1].isdigit() else 0
                
                logger.info(f"=== GA4 CUSTOM PARAMS === Parsed: company={company_name}, recipient={recipient_id}, clicks={event_count}")
                
                total_clicks += event_count
                unique_users += active_users
                
                if company_name and company_name != "(not set)":
                    companies.add(company_name)
                if recipient_id and recipient_id != "(not set)":
                    recipients.add(recipient_id)
        
        analytics_data = {
            'total_clicks': total_clicks,
            'unique_users': unique_users,
            'unique_companies': len(companies),
            'unique_recipients': len(recipients),
            'data_source': 'ga4_custom_dimensions',
            'companies_list': list(companies),
            'recipients_list': list(recipients)
        }
        
        logger.info(f"=== GA4 CUSTOM PARAMS === Final analytics: {analytics_data}")
        return analytics_data

    def _process_custom_clicks_response(self, response) -> List[Dict]:
        """Process GA4 response with confirmed working custom dimensions for detailed clicks"""
        logger.info("=== GA4 CUSTOM PARAMS CLICKS === Processing detailed clicks with confirmed custom dimensions")
        
        detailed_clicks = []
        
        for row in response.rows:
            dims = [dim.value for dim in row.dimension_values]
            metrics = [metric.value for metric in row.metric_values]
            
            logger.info(f"=== GA4 CUSTOM PARAMS CLICKS === Row: dims={dims}, metrics={metrics}")
            
            # dims = [eventName, dateHour, company_name, recipient_id, campaign_id, deviceCategory]
            # metrics = [eventCount]
            
            if len(dims) >= 6 and len(metrics) >= 1:
                event_name = dims[0]
                date_hour = dims[1]
                company_name = dims[2]
                recipient_id = dims[3]
                campaign_id_from_event = dims[4]
                device_category = dims[5]
                
                event_count = int(metrics[0]) if metrics[0].isdigit() else 1
                
                # Parse date_hour (format: YYYYMMDDHH)
                try:
                    if len(date_hour) == 10:  # YYYYMMDDHH
                        year = int(date_hour[:4])
                        month = int(date_hour[4:6])
                        day = int(date_hour[6:8])
                        hour = int(date_hour[8:10])
                        parsed_time = datetime(year, month, day, hour)
                        formatted_time = parsed_time.strftime('%m/%d/%Y, %H:%M:%S')
                    else:
                        formatted_time = date_hour
                except:
                    formatted_time = date_hour
                
                # Create multiple click records if event_count > 1
                for _ in range(event_count):
                    click_record = {
                        'timestamp': formatted_time,
                        'company_name': company_name if company_name != "(not set)" else None,
                        'recipient_email': recipient_id if recipient_id != "(not set)" else "unknown@example.com",
                        'device_type': device_category if device_category != "(not set)" else "Unknown",
                        'location': "Unknown",  # Will add visitor_ip later when custom dimension works
                        'utm_campaign': 'custom_tracking',
                        'visitor_ip': None,  # Will add when custom dimension for visitor_ip works
                        'referrer': None,  # Will add when custom dimension for referrer works
                        'campaign_id': campaign_id_from_event,
                        'data_source': 'ga4_custom_dimensions_basic'
                    }
                    detailed_clicks.append(click_record)
        
        logger.info(f"=== GA4 CUSTOM PARAMS CLICKS === Generated {len(detailed_clicks)} detailed click records")
        return detailed_clicks

# Factory function to create GA4 service instance
def create_ga4_service() -> GA4AnalyticsService:
    """Create Enhanced GA4 Analytics Service with default configuration"""
    logger.info("=== GA4 FACTORY === Creating Enhanced GA4 service with default configuration")
    
    credentials_file = "poetic-hexagon-465803-a5-557cbe7a4d60.json"
    property_id = "496568289"  # Your GA4 property ID
    
    logger.info(f"=== GA4 FACTORY === Using credentials file: {credentials_file}")
    logger.info(f"=== GA4 FACTORY === Using property ID: {property_id}")
    logger.info(f"=== GA4 FACTORY === Looking for credentials file: {os.path.abspath(credentials_file)}")
    
    if not os.path.exists(credentials_file):
        logger.error(f"=== GA4 FACTORY === GA4 credentials file not found: {os.path.abspath(credentials_file)}")
        raise FileNotFoundError(f"GA4 credentials file not found: {credentials_file}")
    
    logger.info(f"=== GA4 FACTORY === Found credentials file, creating enhanced service for property: {property_id}")
    
    try:
        service = GA4AnalyticsService(credentials_file, property_id)
        logger.info("=== GA4 FACTORY === Successfully created Enhanced GA4 service")
        return service
    except Exception as e:
        logger.error(f"=== GA4 FACTORY === Failed to create Enhanced GA4 service: {str(e)}")
        logger.error(f"=== GA4 FACTORY === Exception type: {type(e).__name__}")
        logger.error(f"=== GA4 FACTORY === Traceback: {traceback.format_exc()}")
        raise