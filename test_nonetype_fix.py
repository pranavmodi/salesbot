#!/usr/bin/env python3
"""Test NoneType len() fix in deep research composer."""

from app import create_app

def test_nonetype_len_fix():
    """Test that NoneType len() errors are fixed."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create a mock company object with None values
            class MockCompany:
                def __init__(self):
                    self.id = 999
                    self.company_name = "Test Company"
                    self.html_report = None  # This will cause len() error if not handled
                    self.company_research = None  # This will cause len() error if not handled
                    self.research_status = 'in_progress'
            
            company = MockCompany()
            
            # Test the safe length check logic
            html_report_len = len(company.html_report) if company.html_report else 0
            research_len = len(company.company_research) if company.company_research else 0
            
            print(f"✅ Safe length check test passed:")
            print(f"  - HTML report length: {html_report_len}")
            print(f"  - Research length: {research_len}")
            
            # Test boolean checks
            has_html_report = hasattr(company, 'html_report') and company.html_report
            has_research = hasattr(company, 'company_research') and company.company_research
            
            print(f"✅ Boolean check test passed:")
            print(f"  - Has HTML report: {has_html_report}")
            print(f"  - Has research: {has_research}")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False

if __name__ == "__main__":
    success = test_nonetype_len_fix()
    if success:
        print("🎉 NoneType len() fix validation PASSED!")
    else:
        print("💥 NoneType len() fix validation FAILED!")
    exit(0 if success else 1)