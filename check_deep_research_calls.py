#!/usr/bin/env python3
"""
Deep Research API Call Tracker

Analyzes logs to track all deep research API calls within specified time periods.
Helps identify potential runaway API usage and tracks spending patterns.
"""

import os
import sys
import re
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def parse_log_timestamp(timestamp_str):
    """Parse log timestamp string to datetime object."""
    try:
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        # Try alternative format with microseconds
        try:
            return datetime.strptime(timestamp_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None

def analyze_deep_research_calls(log_file_path, time_periods):
    """
    Analyze deep research API calls from log file within specified time periods.
    
    Args:
        log_file_path: Path to the log file
        time_periods: Dictionary with time period names and timedelta objects
    
    Returns:
        Dictionary with analysis results for each time period
    """
    
    # Patterns to match deep research related log entries
    patterns = {
        'research_start': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Starting LLM step research for company.*?: (.+?), provider=(\w+)'),
        'research_execute': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Starting LLM deep research for company: (.+?) using (\w+)'),
        'openai_api_call': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Starting OpenAI Deep Research API call.*for (.+?)'),
        'claude_api_call': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Executing Claude.*research for (.+?)'),
        'api_error': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Error.*research.*for (.+?):(.+)'),
        'rate_limit': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Rate limit.*research.*for (.+?)'),
        'safety_block': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*BLOCKED.*Research already in progress.*company (\d+)'),
        'request_registered': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*SAFETY: Registered request start for company (\d+)'),
        'request_completed': re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*SAFETY: Request completed for company (\d+).*cost: \$(\d+\.\d+)')
    }
    
    now = datetime.now()
    results = {}
    
    # Initialize results for each time period
    for period_name in time_periods:
        results[period_name] = {
            'total_research_starts': 0,
            'total_api_calls': 0,
            'openai_calls': 0,
            'claude_calls': 0,
            'errors': 0,
            'rate_limits': 0,
            'safety_blocks': 0,
            'estimated_cost': 0.0,
            'companies_affected': set(),
            'call_details': [],
            'error_details': [],
            'safety_events': []
        }
    
    if not os.path.exists(log_file_path):
        print(f"⚠️  Log file not found: {log_file_path}")
        return results
    
    print(f"📊 Analyzing deep research calls from: {log_file_path}")
    print(f"🕐 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Check each pattern
                for pattern_name, pattern in patterns.items():
                    match = pattern.search(line)
                    if match:
                        timestamp_str = match.group(1)
                        timestamp = parse_log_timestamp(timestamp_str)
                        
                        if timestamp is None:
                            continue
                        
                        # Check which time periods this event falls into
                        for period_name, period_delta in time_periods.items():
                            cutoff_time = now - period_delta
                            
                            if timestamp >= cutoff_time:
                                result = results[period_name]
                                
                                if pattern_name == 'research_start':
                                    company_name = match.group(2)
                                    provider = match.group(3)
                                    result['total_research_starts'] += 1
                                    result['companies_affected'].add(company_name)
                                    result['call_details'].append({
                                        'timestamp': timestamp,
                                        'type': 'research_start',
                                        'company': company_name,
                                        'provider': provider,
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'research_execute':
                                    company_name = match.group(2)
                                    provider = match.group(3)
                                    result['total_api_calls'] += 1
                                    result['companies_affected'].add(company_name)
                                    result['call_details'].append({
                                        'timestamp': timestamp,
                                        'type': 'api_execute',
                                        'company': company_name,
                                        'provider': provider,
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'openai_api_call':
                                    company_name = match.group(2)
                                    result['openai_calls'] += 1
                                    result['estimated_cost'] += 0.50  # Estimated cost per OpenAI call
                                    result['companies_affected'].add(company_name)
                                    result['call_details'].append({
                                        'timestamp': timestamp,
                                        'type': 'openai_api',
                                        'company': company_name,
                                        'provider': 'openai',
                                        'estimated_cost': 0.50,
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'claude_api_call':
                                    company_name = match.group(2)
                                    result['claude_calls'] += 1
                                    result['estimated_cost'] += 0.10  # Estimated cost per Claude call
                                    result['companies_affected'].add(company_name)
                                    result['call_details'].append({
                                        'timestamp': timestamp,
                                        'type': 'claude_api',
                                        'company': company_name,
                                        'provider': 'claude',
                                        'estimated_cost': 0.10,
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'api_error':
                                    company_name = match.group(2)
                                    error_msg = match.group(3)
                                    result['errors'] += 1
                                    result['companies_affected'].add(company_name)
                                    result['error_details'].append({
                                        'timestamp': timestamp,
                                        'company': company_name,
                                        'error': error_msg.strip(),
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'rate_limit':
                                    company_name = match.group(2)
                                    result['rate_limits'] += 1
                                    result['companies_affected'].add(company_name)
                                    result['error_details'].append({
                                        'timestamp': timestamp,
                                        'company': company_name,
                                        'error': 'Rate limit exceeded',
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'safety_block':
                                    company_id = match.group(2)
                                    result['safety_blocks'] += 1
                                    result['safety_events'].append({
                                        'timestamp': timestamp,
                                        'type': 'concurrent_block',
                                        'company_id': company_id,
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'request_registered':
                                    company_id = match.group(2)
                                    result['safety_events'].append({
                                        'timestamp': timestamp,
                                        'type': 'request_start',
                                        'company_id': company_id,
                                        'line': line_num
                                    })
                                
                                elif pattern_name == 'request_completed':
                                    company_id = match.group(2)
                                    actual_cost = float(match.group(3))
                                    result['safety_events'].append({
                                        'timestamp': timestamp,
                                        'type': 'request_complete',
                                        'company_id': company_id,
                                        'actual_cost': actual_cost,
                                        'line': line_num
                                    })
    
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return results
    
    # Convert sets to lists for JSON serialization
    for period_name in results:
        results[period_name]['companies_affected'] = list(results[period_name]['companies_affected'])
    
    return results

def print_analysis_report(results, time_periods):
    """Print a comprehensive analysis report."""
    
    for period_name, period_delta in time_periods.items():
        result = results[period_name]
        
        print(f"\n🔍 ANALYSIS FOR LAST {period_name.upper()}")
        print("=" * 60)
        
        # Summary metrics
        print(f"📊 SUMMARY METRICS:")
        print(f"   • Research Sessions Started: {result['total_research_starts']}")
        print(f"   • Total API Calls Made: {result['total_api_calls']}")
        print(f"   • OpenAI API Calls: {result['openai_calls']}")
        print(f"   • Claude API Calls: {result['claude_calls']}")
        print(f"   • Companies Affected: {len(result['companies_affected'])}")
        print(f"   • Estimated Cost: ${result['estimated_cost']:.2f}")
        
        # Error and safety metrics
        print(f"\n⚠️  ERROR & SAFETY METRICS:")
        print(f"   • API Errors: {result['errors']}")
        print(f"   • Rate Limit Hits: {result['rate_limits']}")
        print(f"   • Safety Blocks (Concurrent): {result['safety_blocks']}")
        print(f"   • Safety Events Total: {len(result['safety_events'])}")
        
        # Risk assessment
        risk_level = "🟢 LOW"
        if result['total_api_calls'] > 20 or result['estimated_cost'] > 10.0:
            risk_level = "🟡 MEDIUM"
        if result['total_api_calls'] > 50 or result['estimated_cost'] > 25.0 or result['safety_blocks'] > 0:
            risk_level = "🔴 HIGH"
        
        print(f"\n🚨 RISK ASSESSMENT: {risk_level}")
        
        # Companies affected
        if result['companies_affected']:
            print(f"\n🏢 COMPANIES RESEARCHED ({len(result['companies_affected'])}):")
            for company in sorted(result['companies_affected'])[:10]:  # Show first 10
                print(f"   • {company}")
            if len(result['companies_affected']) > 10:
                print(f"   • ... and {len(result['companies_affected']) - 10} more")
        
        # Recent calls (last 5)
        if result['call_details']:
            print(f"\n📞 RECENT API CALLS (Last 5):")
            recent_calls = sorted(result['call_details'], key=lambda x: x['timestamp'], reverse=True)[:5]
            for call in recent_calls:
                timestamp = call['timestamp'].strftime('%H:%M:%S')
                print(f"   • {timestamp} - {call['type']} - {call['company']} ({call['provider']})")
        
        # Errors
        if result['error_details']:
            print(f"\n❌ ERRORS ({len(result['error_details'])}):")
            for error in result['error_details'][-3:]:  # Show last 3 errors
                timestamp = error['timestamp'].strftime('%H:%M:%S')
                print(f"   • {timestamp} - {error['company']}: {error['error'][:80]}...")
        
        # Safety events
        if result['safety_events']:
            print(f"\n🛡️  SAFETY EVENTS ({len(result['safety_events'])}):")
            for event in result['safety_events'][-3:]:  # Show last 3 events
                timestamp = event['timestamp'].strftime('%H:%M:%S')
                if event['type'] == 'concurrent_block':
                    print(f"   • {timestamp} - BLOCKED concurrent request for company {event['company_id']}")
                elif event['type'] == 'request_complete' and 'actual_cost' in event:
                    print(f"   • {timestamp} - COMPLETED company {event['company_id']}, cost: ${event['actual_cost']:.2f}")

def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(description='Analyze deep research API calls from logs')
    parser.add_argument('--log-file', default='logs/salesbot_activity.log', 
                       help='Path to log file (default: logs/salesbot_activity.log)')
    parser.add_argument('--periods', nargs='+', 
                       default=['10m', '1h', '6h', '24h'],
                       help='Time periods to analyze (default: 10m 1h 6h 24h)')
    
    args = parser.parse_args()
    
    # Convert period strings to timedelta objects
    time_periods = {}
    for period in args.periods:
        if period.endswith('m'):
            minutes = int(period[:-1])
            time_periods[f"{minutes} minutes"] = timedelta(minutes=minutes)
        elif period.endswith('h'):
            hours = int(period[:-1])
            time_periods[f"{hours} hours"] = timedelta(hours=hours)
        elif period.endswith('d'):
            days = int(period[:-1])
            time_periods[f"{days} days"] = timedelta(days=days)
        else:
            print(f"⚠️  Invalid period format: {period} (use format like '10m', '1h', '24h')")
            continue
    
    if not time_periods:
        print("❌ No valid time periods specified")
        return
    
    # Get absolute path to log file
    log_file_path = os.path.abspath(args.log_file)
    
    # Run analysis
    results = analyze_deep_research_calls(log_file_path, time_periods)
    
    # Print report
    print_analysis_report(results, time_periods)
    
    # Final summary
    print("\n" + "=" * 80)
    print("🎯 ANALYSIS COMPLETE")
    
    # Check for any concerning patterns
    total_calls_24h = results.get('24 hours', {}).get('total_api_calls', 0)
    total_cost_24h = results.get('24 hours', {}).get('estimated_cost', 0.0)
    
    if total_calls_24h > 100:
        print("🚨 WARNING: High API usage detected in last 24 hours!")
    if total_cost_24h > 30.0:
        print("🚨 WARNING: High estimated cost in last 24 hours!")
    
    safety_blocks = results.get('24 hours', {}).get('safety_blocks', 0)
    if safety_blocks > 0:
        print(f"✅ GOOD: Safety system blocked {safety_blocks} concurrent requests")
    else:
        print("✅ GOOD: No safety blocks needed (controlled usage)")

if __name__ == '__main__':
    main()