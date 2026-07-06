"""
Startup script for the Mutual Fund FAQ Assistant API server.
Run with: python run.py
"""
import uvicorn
import os
import sys

# Ensure current directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    print("=" * 70)
    print("🚀 Starting Mutual Fund FAQ Assistant RAG Chatbot")
    print(f"📡 API Server:  http://localhost:{port}")
    print(f"📖 API Docs:    http://localhost:{port}/docs")
    print(f"💻 Web UI:      Open src/ui/index.html in your web browser")
    print("=" * 70)
    
    uvicorn.run("src.api.main:app", host=host, port=port, reload=True)
