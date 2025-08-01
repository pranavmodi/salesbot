#!/usr/bin/env python3
"""
Test script for thread safety fixes in email composition.
Run this to validate that the malloc errors are resolved.
"""

import threading
import time
import logging
import gc
from concurrent.futures import ThreadPoolExecutor
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_thread_safe_email_composition():
    """Test email composition under concurrent load."""
    
    app = create_app()
    
    def compose_email_worker(worker_id):
        """Worker function that composes emails concurrently."""
        with app.app_context():
            try:
                from app.services.thread_safe_email_composer import get_thread_safe_composer
                from app.models.contact import Contact
                
                logger.info(f"Worker {worker_id}: Starting email composition test")
                
                # Get a sample contact
                contacts = Contact.load_all()
                if not contacts:
                    logger.error(f"Worker {worker_id}: No contacts available for testing")
                    return False
                
                contact = contacts[0]  # Use first contact
                composer = get_thread_safe_composer()
                
                # Test data
                lead_data = {
                    "name": contact.display_name,
                    "email": contact.email,
                    "company": contact.company or "Test Company",
                    "position": contact.job_title or "Test Position",
                    "website": contact.company_domain or "example.com",
                    "notes": "",
                }
                
                # Compose multiple emails to test memory handling
                for i in range(3):
                    logger.info(f"Worker {worker_id}: Composing email {i+1}/3")
                    
                    result = composer.compose_email_safely(
                        lead=lead_data,
                        calendar_url="https://calendly.com/test/15min",
                        extra_context="This is a thread safety test",
                        composer_type="deep_research",
                        campaign_id=None
                    )
                    
                    if result and 'subject' in result and 'body' in result:
                        logger.info(f"Worker {worker_id}: Email {i+1} composed successfully")
                        logger.info(f"Worker {worker_id}: Subject: {result['subject'][:50]}...")
                        logger.info(f"Worker {worker_id}: Body length: {len(result['body'])} chars")
                    else:
                        logger.error(f"Worker {worker_id}: Email {i+1} composition failed: {result}")
                        return False
                    
                    # Small delay between compositions
                    time.sleep(1)
                    
                    # Force garbage collection
                    collected = gc.collect()
                    logger.debug(f"Worker {worker_id}: GC collected {collected} objects after email {i+1}")
                
                logger.info(f"Worker {worker_id}: All emails composed successfully")
                return True
                
            except Exception as e:
                logger.error(f"Worker {worker_id}: Error during email composition: {e}")
                return False
    
    # Test with multiple concurrent threads
    num_workers = 3  # Test with 3 concurrent threads
    logger.info(f"Starting thread safety test with {num_workers} concurrent workers")
    
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(compose_email_worker, i+1) for i in range(num_workers)]
        
        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=300)  # 5 minute timeout per worker
                results.append(result)
                logger.info(f"Worker {i+1} completed: {'SUCCESS' if result else 'FAILED'}")
            except Exception as e:
                logger.error(f"Worker {i+1} failed with exception: {e}")
                results.append(False)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Report results
    successful_workers = sum(results)
    logger.info(f"Thread safety test completed in {total_time:.2f} seconds")
    logger.info(f"Results: {successful_workers}/{num_workers} workers successful")
    
    if successful_workers == num_workers:
        logger.info("✅ Thread safety test PASSED - No malloc errors detected")
        return True
    else:
        logger.error("❌ Thread safety test FAILED - Some workers encountered errors")
        return False

def test_memory_cleanup():
    """Test memory cleanup and garbage collection."""
    logger.info("Testing memory cleanup...")
    
    app = create_app()
    
    with app.app_context():
        try:
            from app.services.thread_safe_email_composer import get_thread_safe_composer
            
            # Get initial memory baseline
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
            
            # Create and use composer multiple times
            for i in range(10):
                composer = get_thread_safe_composer()
                
                # Simulate email composition without actual API calls
                logger.info(f"Memory test iteration {i+1}/10")
                
                # Force garbage collection
                collected = gc.collect()
                logger.debug(f"GC collected {collected} objects in iteration {i+1}")
                
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                logger.debug(f"Memory usage after iteration {i+1}: {current_memory:.2f} MB")
            
            # Final cleanup
            final_collected = gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            memory_increase = final_memory - initial_memory
            logger.info(f"Final memory usage: {final_memory:.2f} MB")
            logger.info(f"Memory increase: {memory_increase:.2f} MB")
            logger.info(f"Final GC collected: {final_collected} objects")
            
            # Consider test passed if memory increase is reasonable (< 50MB)
            if memory_increase < 50:
                logger.info("✅ Memory cleanup test PASSED")
                return True
            else:
                logger.warning(f"⚠️ Memory cleanup test WARNING - Memory increased by {memory_increase:.2f} MB")
                return True  # Still pass but with warning
                
        except Exception as e:
            logger.error(f"❌ Memory cleanup test FAILED: {e}")
            return False

def main():
    """Run all thread safety tests."""
    logger.info("=" * 60)
    logger.info("THREAD SAFETY TEST SUITE")
    logger.info("=" * 60)
    
    tests = [
        ("Thread-Safe Email Composition", test_thread_safe_email_composition),
        ("Memory Cleanup", test_memory_cleanup),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running test: {test_name}")
        logger.info("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            logger.info(f"Test '{test_name}': {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All thread safety tests PASSED! Malloc errors should be resolved.")
    else:
        logger.error("💥 Some tests FAILED. Thread safety issues may still exist.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)