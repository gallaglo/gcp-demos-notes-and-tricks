import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from animation_graph import run_animation_generation, AnimationState, Message
from dotenv import load_dotenv
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from uuid import uuid4

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for required environment variables
if not os.environ.get("BLENDER_SERVICE_URL"):
    logger.warning("BLENDER_SERVICE_URL environment variable is not set.")
    logger.warning("Please set this variable to the URL of your Blender Cloud Run service.")
    logger.warning("Example: export BLENDER_SERVICE_URL=https://animator-abc123-uc.a.run.app")

app = FastAPI(title="Animation Generator API")

# Add improved CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

# Store active threads (in-memory storage - not persistent)
active_threads = {}

class AnimationRequest(BaseModel):
    prompt: str

class AnimationResponse(BaseModel):
    signed_url: str
    generation_status: str
    error: str = ""

class ThreadRequest(BaseModel):
    messages: List[Dict[str, Any]]
    checkpoint: Optional[str] = None
    command: Optional[Dict[str, Any]] = None

@app.post("/generate")
async def generate_animation(request: AnimationRequest):
    """Endpoint to generate an animation from a prompt."""
    logger.info(f"Received animation request with prompt: {request.prompt}")
    try:
        result = run_animation_generation(request.prompt)
        logger.info(f"Animation generation completed with result: {result}")
        
        # Ensure consistent response structure
        return {
            "signed_url": result.get("signed_url", ""),
            "generation_status": result.get("generation_status", ""),
            "error": result.get("error", "")
        }
    except Exception as e:
        logger.error(f"Error in animation generation: {str(e)}")
        return {
            "signed_url": "",
            "generation_status": "error",
            "error": str(e)
        }

async def process_thread_messages(thread_id: str, 
                                 messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process messages for a thread and return a streaming response.
    
    Args:
        thread_id (str): Thread ID
        messages (List[Dict]): List of message objects
    """
    try:
        # Initialize if this is a new thread
        if thread_id not in active_threads:
            active_threads[thread_id] = {
                "messages": [],
                "status": "initialized",
                "signedUrl": None,
            }
        
        thread_data = active_threads[thread_id]
        
        # Get the history of messages
        history = []
        for msg in thread_data["messages"]:
            history.append({
                "role": msg["type"],  # Convert to role format for the graph
                "content": msg["content"]
            })
        
        # Extract the latest human message
        latest_message = None
        for msg in messages:
            if msg["type"] == "human":
                latest_message = msg["content"]
                
                # Add to thread data
                msg_with_id = {
                    "id": msg.get("id", str(uuid4())),
                    "type": "human",
                    "content": latest_message
                }
                thread_data["messages"].append(msg_with_id)
                
                # Send message event
                yield {
                    "type": "message",
                    "data": msg_with_id
                }
                break
        
        if not latest_message:
            yield {
                "type": "error",
                "error": "No human message provided"
            }
            return
        
        # Send initial state
        yield {
            "type": "state",
            "data": thread_data
        }
        
        # Update status - analyzing
        thread_data["status"] = "analyzing"
        yield {
            "type": "status",
            "data": {"status": "Analyzing your request"}
        }
        
        # Run the animation generation with history
        result = run_animation_generation(latest_message, history)
        
        # Process result
        if result.get("error"):
            thread_data["status"] = "error"
            
            # Add AI error message
            error_message = {
                "id": str(uuid4()),
                "type": "ai",
                "content": f"Error: {result['error']}"
            }
            thread_data["messages"].append(error_message)
            
            yield {
                "type": "message",
                "data": error_message
            }
            
            yield {
                "type": "error",
                "error": result["error"]
            }
        else:
            # Update thread with history from result
            for msg in result.get("history", []):
                if msg["role"] == "ai":
                    ai_message = {
                        "id": str(uuid4()),
                        "type": "ai",
                        "content": msg["content"]
                    }
                    
                    # Check if this message is already in the thread
                    is_new = True
                    for existing_msg in thread_data["messages"]:
                        if existing_msg["type"] == "ai" and existing_msg["content"] == msg["content"]:
                            is_new = False
                            break
                    
                    if is_new:
                        thread_data["messages"].append(ai_message)
                        yield {
                            "type": "message",
                            "data": ai_message
                        }
            
            # If we have a signed URL, send it
            if result.get("signed_url"):
                thread_data["signedUrl"] = result["signed_url"]
                thread_data["status"] = "completed"
                
                yield {
                    "type": "data",
                    "data": {"signed_url": result["signed_url"]}
                }
                
                yield {
                    "type": "status",
                    "data": {"status": "Completed"}
                }
            else:
                # This was just a conversation
                thread_data["status"] = "conversation"
                
                yield {
                    "type": "status",
                    "data": {"status": "Conversation"}
                }
        
        # End the stream
        yield {
            "type": "end"
        }
    except Exception as e:
        logger.error(f"Error processing thread: {str(e)}")
        
        # Send error
        yield {
            "type": "error",
            "error": str(e)
        }

@app.post("/thread/{thread_id}")
async def handle_thread_request(
    thread_id: str,
    request: ThreadRequest,
    background_tasks: BackgroundTasks
):
    """Handle a thread request with SSE streaming."""
    logger.info(f"Received thread request for thread: {thread_id}")
    
    # Create thread ID if not provided
    if thread_id == "new":
        thread_id = str(uuid4())
        logger.info(f"Created new thread with ID: {thread_id}")
    
    # Return a streaming response
    return StreamingResponse(
        stream_thread_events(thread_id, request.messages),
        media_type="text/event-stream"
    )

async def stream_thread_events(thread_id: str, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """Generate streaming events for thread processing."""
    encoder = asyncio.StreamWriter
    
    try:
        # Process the thread messages
        async for event in process_thread_messages(thread_id, messages):
            # Format the event for SSE
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as e:
        logger.error(f"Error in stream: {str(e)}")
        # Send error event
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

@app.get("/thread/{thread_id}")
async def get_thread(thread_id: str):
    """Get the current state of a thread."""
    if thread_id not in active_threads:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    
    return active_threads[thread_id]

@app.options("/{path:path}")
async def preflight_handler(request: Request):
    """Handle preflight OPTIONS requests"""
    return {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)