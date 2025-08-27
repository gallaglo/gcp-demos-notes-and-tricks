"""Main FastAPI Application for ADK Animation Agent"""
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Import ADK agent components
from agent import animation_workflow, conversation_agent

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
    """
    logger.info(f"Received animation request with prompt: {request.prompt}")
    
    try:
        # Use ADK animation workflow to process the request
        result = await animation_workflow.run({"user_input": request.prompt})
        
        # Extract results from the workflow
        if result and "final_result" in result:
            final_result = result["final_result"]
            
            # Check if we got a successful animation generation
            if "signed_url" in final_result:
                return {
                    "signed_url": final_result["signed_url"],
                    "generation_status": "completed",
                    "error": ""
                }
            elif "error" in final_result:
                return {
                    "signed_url": "",
                    "generation_status": "error",
                    "error": final_result["error"]
                }
        
        # Default response if workflow doesn't return expected format
        return {
            "signed_url": "",
            "generation_status": "processing",
            "error": ""
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
    Handle thread requests - uses ADK agents for processing.
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
        
        # Use ADK agents to process the request
        # First determine if this is an animation request or conversation
        try:
            # Try animation workflow first
            result = await animation_workflow.run({"user_input": latest_message})
            
            if result and "final_result" in result:
                final_result = result["final_result"]
                
                if "signed_url" in final_result:
                    # Animation was generated successfully
                    response_content = f"Animation generated successfully! You can view it here: {final_result['signed_url']}"
                elif "error" in final_result:
                    response_content = f"Error generating animation: {final_result['error']}"
                else:
                    response_content = "Animation is being processed."
            else:
                response_content = "Processing your animation request..."
                
        except Exception as e:
            # If animation workflow fails, try conversation agent
            logger.info(f"Animation workflow failed, trying conversation: {str(e)}")
            try:
                conv_result = await conversation_agent.run({"user_input": latest_message})
                if conv_result and "conversation_result" in conv_result:
                    response_content = conv_result["conversation_result"]
                else:
                    response_content = "I'm here to help with 3D animation generation and related questions."
            except Exception as conv_e:
                logger.error(f"Conversation agent also failed: {str(conv_e)}")
                response_content = "I apologize, but I'm experiencing technical difficulties. Please try again later."
        
        response_message = {
            "id": f"msg_{thread_id}_{len(request.messages)}",
            "type": "ai", 
            "content": response_content
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