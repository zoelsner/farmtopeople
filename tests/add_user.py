#!/usr/bin/env python3
"""
Add your Farm to People credentials to the database.
Update the credentials below and run this script.
"""
import os
import sys
sys.path.append('server')

# Set environment variables for this script
os.environ['SUPABASE_URL'] = 'https://zybssxnapxqziolkozjy.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5YnNzeG5hcHhxemlvbGtvemp5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDgwMDAwOSwiZXhwIjoyMDcwMzc2MDA5fQ.3clL8JnUJIF2lAE9CJwCNqriGKxIc54wEISNdUsXV1I'

# ADD YOUR FARM TO PEOPLE CREDENTIALS HERE:
PHONE_NUMBER = "14254955323"  # Your phone number for testing
FTP_EMAIL = "your_actual_email@domain.com"     # REPLACE WITH YOUR ACTUAL EMAIL
FTP_PASSWORD = "your_actual_password"           # REPLACE WITH YOUR ACTUAL PASSWORD

if FTP_EMAIL == "your_email@example.com" or FTP_PASSWORD == "your_password_here":
    print("❌ Please update your Farm to People credentials in this script first!")
    print("   Edit add_user.py and set FTP_EMAIL and FTP_PASSWORD")
    sys.exit(1)

try:
    import supabase_client as db
    
    print(f"🔄 Adding user {PHONE_NUMBER} to database...")
    
    result = db.upsert_user_credentials(
        phone_number=PHONE_NUMBER,
        ftp_email=FTP_EMAIL,
        ftp_password=FTP_PASSWORD,
        preferences={}
    )
    
    print("✅ User added successfully!")
    print(f"   Phone: {result.get('phone_number')}")
    print(f"   Email: {result.get('ftp_email')}")
    print(f"   ID: {result.get('id')}")
    
    # Test lookup
    print(f"\n🔍 Testing lookup for {PHONE_NUMBER}...")
    user = db.get_user_by_phone(PHONE_NUMBER)
    if user:
        print("✅ User lookup successful!")
        print(f"   Found email: {user.get('ftp_email')}")
    else:
        print("❌ User lookup failed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
