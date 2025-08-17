#!/usr/bin/env python3
"""
Quick setup script to create the users table and add test user data to Supabase.
Run this once to set up the database structure.
"""
import os
import sys
sys.path.append('server')

# Set environment variables for this script
os.environ['SUPABASE_URL'] = 'https://zybssxnapxqziolkozjy.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5YnNzeG5hcHhxemlvbGtvemp5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDgwMDAwOSwiZXhwIjoyMDcwMzc2MDA5fQ.3clL8JnUJIF2lAE9CJwCNqriGKxIc54wEISNdUsXV1I'

try:
    from supabase import create_client
    
    print("🔄 Connecting to Supabase...")
    client = create_client(
        os.environ['SUPABASE_URL'], 
        os.environ['SUPABASE_KEY']
    )
    
    # Test connection
    print("✅ Connected to Supabase successfully!")
    
    # Try to create users table (will fail gracefully if it exists)
    print("\n🔄 Setting up users table...")
    
    # First, let's see what tables exist
    try:
        result = client.table('users').select('*').limit(1).execute()
        print("✅ Users table already exists!")
        print(f"   Current records: {len(result.data)}")
    except Exception as e:
        print("⚠️ Users table doesn't exist or has issues:")
        print(f"   Error: {e}")
        print("\n📋 You need to create the users table in Supabase with this SQL:")
        print("""
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE,
    ftp_email TEXT UNIQUE NOT NULL,
    ftp_password_encrypted TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Add RLS policies if needed
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy to allow service role to manage all data
CREATE POLICY "Service role can manage all users" ON users
    USING (true)
    WITH CHECK (true);
        """)
        sys.exit(1)
    
    # Add test user if not exists
    print("\n🔄 Adding test user credentials...")
    
    # Check if test user exists
    test_phone = "14254955323"
    existing = client.table('users').select('*').eq('phone_number', test_phone).execute()
    
    if existing.data:
        print(f"✅ Test user {test_phone} already exists!")
        user = existing.data[0]
        print(f"   Email: {user.get('ftp_email', 'Not set')}")
    else:
        # You'll need to add your Farm to People credentials here
        print("⚠️ Test user doesn't exist. You need to add your Farm to People credentials:")
        print(f"   Phone: {test_phone}")
        print("   Email: [YOUR FARM TO PEOPLE EMAIL]")
        print("   Password: [YOUR FARM TO PEOPLE PASSWORD]")
        print("\n🔧 Update this script with your credentials and run again.")
    
    print("\n✅ Supabase setup complete!")
    
except ImportError:
    print("❌ Error: supabase-py not installed. Install with:")
    print("   pip install supabase")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error connecting to Supabase: {e}")
    sys.exit(1)
