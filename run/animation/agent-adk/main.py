"""Main FastAPI Application for ADK Animation Agent"""
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ADK Animation Agent API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

# Request/Response models
class AnimationRequest(BaseModel):
    prompt: str

class ThreadRequest(BaseModel):
    messages: List[Dict[str, Any]]
    checkpoint: Optional[str] = None
    command: Optional[Dict[str, Any]] = None

class AnimationResponse(BaseModel):
    signed_url: str
    generation_status: str
    error: str = ""

# Temporary storage for active threads (in production, use proper storage)
active_threads = {}

@app.post("/generate")
async def generate_animation(request: AnimationRequest):
    """
    Endpoint to generate an animation from a prompt using ADK agents.
    
    Note: This is a compatibility endpoint that mimics the original LangGraph interface.
    In a full ADK implementation, this would be handled by the ADK runtime.
    """
    logger.info(f"Received animation request with prompt: {request.prompt}")
    
    try:
        # For now, return a placeholder response
        # In a full implementation, this would invoke the ADK agent workflow
        
        return {
            "signed_url": "",
            "generation_status": "adk_migration_in_progress", 
            "error": "ADK agent system is being implemented. Please use the original agent service for now."
        }
        
    except Exception as e:
        logger.error(f"Error in animation generation: {str(e)}")
        return {
            "signed_url": "",
            "generation_status": "error",
            "error": str(e)
        }

@app.post("/thread/{thread_id}")
async def handle_thread_request(thread_id: str, request: ThreadRequest):
    """
    Handle thread requests - compatibility endpoint for the existing frontend.
    
    Note: This maintains compatibility with the existing streaming interface
    while the ADK implementation is being completed.
    """
    logger.info(f"Received thread request for thread: {thread_id}")
    
    try:
        # Extract the latest human message
        latest_message = None
        for msg in request.messages:
            if msg.get("type") == "human":
                latest_message = msg.get("content")
                break
        
        if not latest_message:
            raise HTTPException(status_code=400, detail="No human message provided")
        
        # For now, return a placeholder response indicating ADK migration
        response_message = {
            "id": "adk_migration_msg",
            "type": "ai", 
            "content": "The ADK-based animation agent is being implemented. The system now includes:\n\n1. ✅ Analysis Agent - Determines user intent\n2. ✅ Script Generation Agent - Creates Blender scripts\n3. ✅ Storage Agent - Handles cloud storage uploads\n4. ✅ Rendering Agent - Coordinates with Blender service\n\nThe migration separates the cloud storage logic from the animator service as requested. Please use the original agent service while the ADK integration is completed."
        }
        
        return {
            "type": "message",
            "data": response_message
        }
        
    except Exception as e:
        logger.error(f"Error processing thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/thread/{thread_id}")
async def get_thread(thread_id: str):
    """Get the current state of a thread."""
    if thread_id not in active_threads:
        return {
            "messages": [],
            "status": "adk_migration",
            "signedUrl": None
        }
    
    return active_threads[thread_id]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "adk-animation-agent",
        "migration_status": "in_progress"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting ADK Animation Agent on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)