#!/usr/bin/env python3
"""
Quick Start Script for ATS Lead Generation Tool

This script helps you get started with company seeding and scraping quickly.
"""

import os
import sys
from company_seeder import CompanySeeder

def quick_seed_demo():
    """Quick seeding with sample data for demo purposes"""
    print("🚀 Quick Start: ATS Lead Generation Tool")
    print("=" * 50)
    
    seeder = CompanySeeder()
    
    # Step 1: Get sample companies (no API key needed)
    print("\n📋 Step 1: Loading sample companies...")
    yc_companies = seeder.seed_from_yc_companies()
    print(f"   ✅ Loaded {len(yc_companies)} sample companies")
    
    # Step 2: Filter companies
    print("\n🔍 Step 2: Applying filters...")
    filtered_companies = seeder.filter_companies(
        yc_companies,
        min_employees=50,
        max_employees=100,
        exclude_industries=['AI/ML', 'Machine Learning']
    )
    print(f"   ✅ Filtered to {len(filtered_companies)} qualified companies")
    
    # Step 3: Save to CSV
    print("\n💾 Step 3: Saving companies...")
    csv_file = seeder.save_companies_to_csv(filtered_companies, "demo_companies.csv")
    print(f"   ✅ Saved to {csv_file}")
    
    # Step 4: Show next steps
    print("\n🎯 Next Steps:")
    print("1. Optional: Get Apollo.io API key for 3k+ companies:")
    print("   - Sign up at https://apollo.io/")
    print("   - export APOLLO_API_KEY='your_key_here'")
    print("   - Run: python company_seeder.py")
    print("")
    print("2. Start the web application:")
    print("   uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    print("")
    print("3. Open browser: http://localhost:8000")
    print("4. Use 'Load Seeded Companies' option in the interface")
    print("")
    print(f"✅ Demo setup complete! {len(filtered_companies)} companies ready for ATS scraping.")

def check_environment():
    """Check if environment is properly set up"""
    print("\n🔍 Environment Check:")
    print("-" * 30)
    
    # Check Python packages
    try:
        import requests
        import fastapi
        import uvicorn
        print("✅ Required packages installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    # Check directories
    if not os.path.exists("data"):
        os.makedirs("data")
        print("✅ Created data directory")
    
    if not os.path.exists("static"):
        print("❌ Static directory missing (should contain index.html)")
        return False
    else:
        print("✅ Static directory found")
    
    # Check API keys (optional)
    apollo_key = os.getenv('APOLLO_API_KEY')
    clearbit_key = os.getenv('CLEARBIT_API_KEY')
    
    print(f"🔑 Apollo.io API Key: {'✅ Set' if apollo_key else '⚠️  Not set (optional)'}")
    print(f"🔑 Clearbit API Key: {'✅ Set' if clearbit_key else '⚠️  Not set (optional)'}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_environment()
    else:
        if check_environment():
            quick_seed_demo()
        else:
            print("\n❌ Environment issues detected. Please fix and try again.")