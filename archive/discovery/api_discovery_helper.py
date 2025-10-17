"""
Adobe Helper - API Discovery Assistant

This script will help you document the API endpoints you discover.
Run this while you perform the Chrome DevTools analysis.
"""

import json
from pathlib import Path
from datetime import datetime

def create_discovery_template():
    """Create a template for documenting discovered endpoints"""
    
    template = {
        "discovery_date": datetime.now().isoformat(),
        "status": "in_progress",
        "endpoints": {
            "upload": {
                "url": "",
                "method": "POST",
                "headers": {},
                "payload_type": "",
                "response_fields": [],
                "notes": "Look for: Large POST request matching PDF file size"
            },
            "conversion": {
                "url": "",
                "method": "POST",
                "headers": {},
                "payload_example": {},
                "response_fields": [],
                "notes": "Look for: POST request after upload with job/conversion start"
            },
            "status": {
                "url": "",
                "method": "GET",
                "headers": {},
                "polling_interval": "2-5 seconds",
                "response_fields": [],
                "notes": "Look for: Repeated GET requests with job ID in URL"
            }
        },
        "instructions": [
            "1. Open: https://www.adobe.com/acrobat/online/pdf-to-word.html",
            "2. Press F12 (Chrome DevTools)",
            "3. Go to Network tab",
            "4. Check 'Preserve log'",
            "5. Filter: Only 'Fetch/XHR'",
            "6. Upload a small PDF",
            "7. Document the 3 endpoints below",
            "8. Run: python -m adobe.cli.api_discovery_helper update"
        ]
    }
    
    output_file = Path("discovered_endpoints.json")
    with open(output_file, "w") as f:
        json.dump(template, f, indent=2)
    
    print(f"✓ Created discovery template: {output_file}")
    print("\nNext steps:")
    print("1. Open Chrome and go to Adobe's PDF-to-Word page")
    print("2. Follow the instructions in discovered_endpoints.json")
    print("3. Fill in the endpoint URLs as you find them")
    print("4. Run this script again to validate")
    
    return output_file

def show_checklist():
    """Display a step-by-step checklist"""
    
    checklist = """
╔══════════════════════════════════════════════════════════════════════╗
║                  API DISCOVERY CHECKLIST                             ║
╚══════════════════════════════════════════════════════════════════════╝

SETUP (5 minutes)
─────────────────────────────────────────────────────────────────────
☐ Open Chrome browser
☐ Navigate to: https://www.adobe.com/acrobat/online/pdf-to-word.html
☐ Press F12 (or Cmd+Option+I on Mac)
☐ Click "Network" tab
☐ ✓ Check "Preserve log" checkbox
☐ Clear existing logs (trash icon)
☐ Filter: Uncheck "All", check only "Fetch/XHR"

PREPARE TEST FILE (2 minutes)
─────────────────────────────────────────────────────────────────────
☐ Create or find a small PDF file (1-2 pages, < 1MB)
☐ Keep Chrome DevTools open and visible

UPLOAD & CAPTURE (10 minutes)
─────────────────────────────────────────────────────────────────────
☐ Click "Select a file" on Adobe's page
☐ Choose your test PDF
☐ Watch Network tab fill with requests
☐ Wait for conversion to complete (download button appears)

FIND UPLOAD ENDPOINT (5 minutes)
─────────────────────────────────────────────────────────────────────
Look for:
☐ Method: POST
☐ Size: Large (matches your PDF size)
☐ Type: fetch or xhr
☐ Status: 200 or 201

Click on it and document:
☐ Full URL (from Headers → General → Request URL)
☐ Request Headers (look for X-CSRF-Token, Authorization)
☐ Request Payload (multipart/form-data? base64? raw?)
☐ Response (contains uploadId or similar?)

FIND CONVERSION ENDPOINT (5 minutes)
─────────────────────────────────────────────────────────────────────
Look for:
☐ Method: POST (happens right after upload)
☐ Size: Small (JSON payload, not the file)
☐ Type: fetch or xhr

Click on it and document:
☐ Full URL
☐ Payload tab (contains uploadId, targetFormat, feature?)
☐ Response tab (contains jobId, status?)

FIND STATUS ENDPOINT (5 minutes)
─────────────────────────────────────────────────────────────────────
Look for:
☐ Method: GET
☐ Repeats every 2-5 seconds
☐ URL contains job/conversion ID

Click on it and document:
☐ Full URL pattern (replace job ID with {jobId})
☐ Response when processing (status: "processing"?)
☐ Response when complete (status: "completed", downloadUrl?)

UPDATE CODE (2 minutes)
─────────────────────────────────────────────────────────────────────
☐ Edit: adobe/client.py
☐ Find lines 177-179
☐ Replace placeholder URLs with discovered URLs
☐ Save file

TEST (5 minutes)
─────────────────────────────────────────────────────────────────────
☐ Run: uv run python examples/adobe/basic_usage.py
☐ Check for successful conversion
☐ Verify output file exists

╔══════════════════════════════════════════════════════════════════════╗
║  ESTIMATED TIME: 30-40 minutes                                       ║
║  DIFFICULTY: Easy (just copy URLs from Chrome DevTools)             ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(checklist)

def validate_discovery():
    """Validate discovered endpoints"""
    
    discovery_file = Path("discovered_endpoints.json")
    
    if not discovery_file.exists():
        print("❌ No discovery file found. Run: python -m adobe.cli.api_discovery_helper")
        return False
    
    with open(discovery_file) as f:
        data = json.load(f)
    
    print("\n🔍 Validating discovered endpoints...\n")
    
    all_valid = True
    
    for endpoint_name, endpoint_data in data["endpoints"].items():
        url = endpoint_data.get("url", "")
        
        if not url:
            print(f"❌ {endpoint_name.upper()}: Missing URL")
            all_valid = False
        elif url.startswith("http"):
            print(f"✓ {endpoint_name.upper()}: {url[:60]}...")
        else:
            print(f"⚠️  {endpoint_name.upper()}: Invalid URL format")
            all_valid = False
    
    if all_valid:
        print("\n✅ All endpoints discovered!")
        print("\nNext step: Update adobe/client.py")
        print(f"  Upload URL:     {data['endpoints']['upload']['url']}")
        print(f"  Conversion URL: {data['endpoints']['conversion']['url']}")
        print(f"  Status URL:     {data['endpoints']['status']['url']}")
        return True
    else:
        print("\n⚠️  Some endpoints are missing. Continue discovery in Chrome DevTools.")
        return False

if __name__ == "__main__":
    import sys
    
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║         Adobe Helper - API Discovery Assistant                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate_discovery()
    elif len(sys.argv) > 1 and sys.argv[1] == "checklist":
        show_checklist()
    else:
        # Create template
        create_discovery_template()
        print("\n" + "="*70)
        print("\n📋 Want to see the full checklist?")
        print("   Run: python -m adobe.cli.api_discovery_helper checklist")
        print("\n🔍 Ready to validate your discoveries?")
        print("   Run: python -m adobe.cli.api_discovery_helper validate")
