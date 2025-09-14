#!/usr/bin/env python3
"""
Development server runner for Criptify Backend
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info",
    )
