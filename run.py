#!/usr/bin/env python3
"""
Entry point to run the scraper and start the application.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.scrape import build_knowledge_base

if __name__ == "__main__":
    print("Building knowledge base from DarGlobal and Wasalt data...")
    chunks = build_knowledge_base()
    print(f"\n✓ Knowledge base ready with {len(chunks)} chunks.")
    print("\nStarting chatbot server...")
    os.system("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
