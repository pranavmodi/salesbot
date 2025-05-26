#!/usr/bin/env python3
"""
Test script to demonstrate Zoho error detection and automatic pausing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from send_emails import RateLimiter, RATE_LIMIT_CONFIG
import time

def test_zoho_error_detection():
    """Test the Zoho error detection and pausing functionality."""
    
    print("🧪 Testing Zoho Error Detection and Auto-Pause")
    print("=" * 50)
    
    # Create a rate limiter
    rate_limiter = RateLimiter()
    
    # Test 1: Normal operation
    print("\n1. Testing normal operation:")
    can_send, reason = rate_limiter.can_send_email()
    print(f"   Can send: {can_send}, Reason: {reason}")
    
    # Simulate successful send
    rate_limiter.record_send_attempt(True)
    print("   ✓ Recorded successful send")
    
    # Test 2: Simulate Zoho spam detection error
    print("\n2. Simulating Zoho spam detection error:")
    zoho_error = "550, b'5.4.6 Unusual sending activity detected. Please try after sometime.'"
    
    rate_limiter.record_send_attempt(False, zoho_error)
    print(f"   ✗ Recorded Zoho error: {zoho_error}")
    
    # Check status after error
    status = rate_limiter.get_status_info()
    print(f"   Zoho errors detected: {status['zoho_errors_detected']}")
    print(f"   Is paused: {status['is_paused']}")
    print(f"   Pause reason: {status['pause_reason']}")
    print(f"   Current delay: {status['current_delay']:.1f}s")
    
    # Test 3: Check if sending is blocked
    print("\n3. Testing if sending is blocked:")
    can_send, reason = rate_limiter.can_send_email()
    print(f"   Can send: {can_send}")
    print(f"   Reason: {reason}")
    
    # Test 4: Simulate second Zoho error
    print("\n4. Simulating second Zoho error:")
    rate_limiter.record_send_attempt(False, zoho_error)
    
    status = rate_limiter.get_status_info()
    print(f"   Zoho errors detected: {status['zoho_errors_detected']}")
    print(f"   Is paused: {status['is_paused']}")
    print(f"   Pause reason: {status['pause_reason']}")
    
    # Test 5: Test other error types
    print("\n5. Testing non-Zoho error:")
    generic_error = "Connection timeout"
    rate_limiter.record_send_attempt(False, generic_error)
    
    status = rate_limiter.get_status_info()
    print(f"   Zoho errors detected: {status['zoho_errors_detected']}")
    print(f"   Consecutive failures: {status['consecutive_failures']}")
    print(f"   Current delay: {status['current_delay']:.1f}s")
    
    # Test 6: Test error pattern detection
    print("\n6. Testing error pattern detection:")
    test_errors = [
        "550, b'5.4.6 Unusual sending activity detected. Please try after sometime.'",
        "Spam detected by server",
        "Rate limit exceeded",
        "Too many emails sent",
        "Daily quota exceeded",
        "Connection refused",  # This should NOT be detected as Zoho error
        "Invalid credentials"  # This should NOT be detected as Zoho error
    ]
    
    for error in test_errors:
        is_zoho = rate_limiter.detect_zoho_error(error)
        print(f"   '{error[:50]}...' -> Zoho error: {is_zoho}")
    
    print("\n" + "=" * 50)
    print("✅ Zoho error detection test completed!")
    print("\nKey features demonstrated:")
    print("• Automatic detection of Zoho spam warnings")
    print("• Progressive pausing (15min → 1hr → 4hr)")
    print("• Increased delays after Zoho errors")
    print("• Distinction between Zoho and generic errors")
    print("• Status tracking for UI display")

if __name__ == "__main__":
    test_zoho_error_detection() 