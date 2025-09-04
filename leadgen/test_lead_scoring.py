#!/usr/bin/env python3
"""
Test script for the advanced lead scoring system
"""

import asyncio
import sys
import json
from sqlalchemy.orm import Session
from database import get_db_session
from models import Company
from lead_scoring import score_company_by_id, save_lead_score_to_db, score_multiple_companies

async def test_single_company(company_id: int):
    """Test scoring a single company"""
    print(f"🎯 Testing lead scoring for company ID: {company_id}")
    
    # Get company info
    db = next(get_db_session())
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            print(f"❌ Company {company_id} not found")
            return
        
        print(f"📊 Company: {company.name} ({company.domain})")
        print(f"🏢 Industry: {company.industry or 'Unknown'}")
        print(f"👥 Employees: {company.employee_count or 'Unknown'}")
        print("\n" + "="*60 + "\n")
        
    finally:
        db.close()
    
    try:
        # Score the company
        score = await score_company_by_id(company_id)
        
        # Display results
        print("📈 LEAD SCORING RESULTS")
        print("="*60)
        print(f"🎯 Overall Score: {score.overall_score}/400")
        print()
        
        print("📊 Category Breakdowns:")
        print(f"  💬 Support Intensity: {score.support_intensity_total}/500")
        print(f"    • Infrastructure: {score.support_infrastructure_score}/100")
        print(f"    • KB Depth: {score.kb_depth_score}/100") 
        print(f"    • Post-Purchase: {score.post_purchase_score}/100")
        print(f"    • Support Tools: {score.support_tooling_score}/100")
        print(f"    • Reviews/Complaints: {score.review_complaint_score}/100")
        print()
        
        print(f"  🌐 Digital Presence: {score.digital_presence_total}/400")
        print(f"    • Sitemap Density: {score.sitemap_density_score}/100")
        print(f"    • FAQ Richness: {score.faq_richness_score}/100")
        print(f"    • Traffic Scale: {score.traffic_scale_score}/100") 
        print(f"    • Catalog Size: {score.catalog_size_score}/100")
        print()
        
        print(f"  📈 Growth Signals: {score.growth_signals_total}/300")
        print(f"    • Hiring Velocity: {score.hiring_velocity_score}/100")
        print(f"    • Headcount Growth: {score.headcount_growth_score}/100")
        print(f"    • Recent Funding: {score.recent_funding_score}/100")
        print()
        
        print(f"  🛠️  Implementation Feasibility: {score.implementation_feasibility_total}/400")
        print(f"    • Small Tech Team: {score.small_tech_team_score}/100")
        print(f"    • No AI Roles: {score.no_ai_roles_score}/100")
        print(f"    • No Existing Bot: {score.no_existing_bot_score}/100")
        print(f"    • Chat Ready: {score.chat_ready_score}/100")
        print()
        
        # Save to database
        save_lead_score_to_db(score)
        print("✅ Score saved to database")
        
        # Show detailed signal data
        if score.signals_data:
            print("\n🔍 DETAILED SIGNAL ANALYSIS")
            print("="*60)
            for signal_type, data in score.signals_data.items():
                if isinstance(data, dict) and 'reasoning' in data:
                    print(f"\n{signal_type.replace('_', ' ').title()}:")
                    print(f"  Score: {data.get('score', 0)}/100")
                    print(f"  Reasoning: {data.get('reasoning', 'No reasoning provided')}")
        
        return score
        
    except Exception as e:
        print(f"❌ Error scoring company: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_multiple_companies(company_ids: list):
    """Test scoring multiple companies"""
    print(f"🎯 Testing batch lead scoring for {len(company_ids)} companies")
    
    results = await score_multiple_companies(company_ids)
    
    print(f"\n📈 BATCH SCORING RESULTS ({len(results)} completed)")
    print("="*60)
    
    # Sort by score
    results.sort(key=lambda x: x.overall_score, reverse=True)
    
    for i, score in enumerate(results, 1):
        print(f"{i:2d}. {score.company_name:<30} {score.overall_score:3d}/400")
        
        # Save each score
        save_lead_score_to_db(score)
    
    print(f"\n✅ All {len(results)} scores saved to database")
    return results

def list_companies():
    """List available companies for testing"""
    db = next(get_db_session())
    try:
        companies = db.query(Company).filter(Company.is_active == True).limit(20).all()
        
        print("📋 AVAILABLE COMPANIES FOR TESTING")
        print("="*60)
        for company in companies:
            scored = "✅" if company.lead_scored_at else "⏳"
            print(f"{scored} ID:{company.id:3d} | {company.name:<30} | {company.domain or 'No domain'}")
        
        print(f"\nTotal companies: {db.query(Company).filter(Company.is_active == True).count()}")
        
    finally:
        db.close()

async def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("🎯 Lead Scoring Test Tool")
        print("="*30)
        print("Usage:")
        print("  python test_lead_scoring.py list                    # List companies")
        print("  python test_lead_scoring.py score <company_id>      # Score single company")
        print("  python test_lead_scoring.py batch <id1,id2,id3...>  # Score multiple companies")
        print("  python test_lead_scoring.py auto 5                  # Score first 5 unscored companies")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_companies()
        
    elif command == "score":
        if len(sys.argv) < 3:
            print("❌ Please provide a company ID")
            return
        
        try:
            company_id = int(sys.argv[2])
            await test_single_company(company_id)
        except ValueError:
            print("❌ Invalid company ID")
            
    elif command == "batch":
        if len(sys.argv) < 3:
            print("❌ Please provide comma-separated company IDs")
            return
        
        try:
            company_ids = [int(x.strip()) for x in sys.argv[2].split(',')]
            await test_multiple_companies(company_ids)
        except ValueError:
            print("❌ Invalid company IDs")
            
    elif command == "auto":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        
        # Find unscored companies
        db = next(get_db_session())
        try:
            companies = db.query(Company).filter(
                Company.lead_scored_at.is_(None),
                Company.is_active == True,
                Company.domain.isnot(None)  # Only companies with domains
            ).limit(limit).all()
            
            if not companies:
                print("✅ No unscored companies found")
                return
            
            company_ids = [c.id for c in companies]
            print(f"🎯 Auto-scoring {len(company_ids)} unscored companies:")
            for c in companies:
                print(f"  • {c.name} ({c.domain})")
            
            print()
            await test_multiple_companies(company_ids)
            
        finally:
            db.close()
            
    else:
        print("❌ Unknown command. Use 'list', 'score', 'batch', or 'auto'")

if __name__ == "__main__":
    asyncio.run(main())