"""
Test script to verify Neon PostgreSQL connection and pgvector extension.
Run this after setting up your .env file with DATABASE_URL.
"""

import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

def test_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in .env file.")
        print("   Make sure your .env file has: DATABASE_URL=postgresql://...")
        return

    print("🔍 Found DATABASE_URL, attempting to connect...")

    try:
        # Connect to Neon Postgres
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        print("✅ Successfully connected to Neon PostgreSQL!")

        # Check Postgres version
        cursor.execute("SELECT version();")
        pg_version = cursor.fetchone()[0]
        print(f"📦 Postgres version: {pg_version}")

        # Check pgvector extension
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()

        if result:
            print(f"✅ pgvector extension found! Name: {result[0]}, Version: {result[1]}")
        else:
            print("❌ pgvector extension NOT found. Run: CREATE EXTENSION IF NOT EXISTS vector;")

        cursor.close()
        conn.close()
        print("🎉 Connection test completed successfully. Setup looks good!")

    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    test_connection()