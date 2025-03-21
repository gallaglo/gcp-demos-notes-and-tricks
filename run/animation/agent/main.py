import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from animation_graph import run_animation_generation, generate_blender_script, render_animation, AnimationState
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

async def run_animation_generation_stream(prompt: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
    """Async version of run_animation_generation that yields events for streaming."""
    # Initialize the state
    initial_state = AnimationState(
        prompt=prompt,
        blender_script="",
        generation_status="started",
        signed_url="",
        error=""
    )
    
    # Send starting message event
    yield {
        "type": "message",
        "data": {
            "id": str(uuid4()),
            "type": "ai",
            "content": f"Starting to generate animation for: {prompt}"
        }
    }
    
    try:
        # First node: Generate script
        yield {
            "type": "status",
            "data": {"status": "generating_script"}
        }
        
        # Start script generation
        updated_state = generate_blender_script(initial_state)
        
        # Check for errors
        if updated_state.get("error"):
            yield {
                "type": "message",
                "data": {
                    "id": str(uuid4()),
                    "type": "ai",
                    "content": f"Error generating script: {updated_state['error']}"
                }
            }
            yield {
                "type": "error",
                "error": updated_state["error"]
            }
            return
            
        # Script generated successfully
        yield {
            "type": "message",
            "data": {
                "id": str(uuid4()),
                "type": "ai",
                "content": "Script generated successfully. Starting rendering..."
            }
        }
        
        # Second node: Render animation
        yield {
            "type": "status",
            "data": {"status": "rendering"}
        }
        
        # Allow a small delay for UI updates
        await asyncio.sleep(0.5)
        
        # Start rendering
        final_state = render_animation(updated_state)
        
        # Check for errors
        if final_state.get("error"):
            yield {
                "type": "message",
                "data": {
                    "id": str(uuid4()),
                    "type": "ai",
                    "content": f"Error rendering animation: {final_state['error']}"
                }
            }
            yield {
                "type": "error",
                "error": final_state["error"]
            }
            return
            
        # Rendering completed
        yield {
            "type": "message",
            "data": {
                "id": str(uuid4()),
                "type": "ai",
                "content": "Animation rendered successfully! You can view it at the signed URL."
            }
        }
        
        # Send final data event with the signed URL
        yield {
            "type": "data",
            "data": {
                "signed_url": final_state["signed_url"]
            }
        }
        
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        yield {
            "type": "message",
            "data": {
                "id": str(uuid4()),
                "type": "ai",
                "content": f"An unexpected error occurred: {str(e)}"
            }
        }
        yield {
            "type": "error",
            "error": str(e)
        }

async def stream_graph_events(thread_id: str, 
                             state: Dict[str, Any],
                             checkpoint: Optional[str] = None,
                             command: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
    """Generate streaming events from the graph execution."""
    try:
        # Initialize if this is a new thread
        if thread_id not in active_threads:
            active_threads[thread_id] = {
                "messages": [],
                "branches": {},
                "current_branch": "main"
            }
        
        thread_data = active_threads[thread_id]
        
        # Send initial state event
        yield f"data: {json.dumps({'type': 'state', 'data': thread_data})}\n\n"
        
        # Extract prompt from human messages
        prompt = ""
        for msg in state.get("messages", []):
            if isinstance(msg, dict) and msg.get("type") == "human":
                prompt = msg.get("content", "")
                # Store human message
                msg_id = str(uuid4())
                thread_data["messages"].append({
                    "id": msg_id,
                    "type": "human",
                    "content": prompt
                })
                yield f"data: {json.dumps({'type': 'message', 'data': {'id': msg_id, 'type': 'human', 'content': prompt}})}\n\n"
                break
        
        if not prompt:
            yield f"data: {json.dumps({'type': 'error', 'error': 'No prompt provided'})}\n\n"
            return
            
        # Execute the graph with streaming
        async for event in run_animation_generation_stream(prompt, **({} if not command else {"command": command})):
            # Format the event according to server-sent events protocol
            if event["type"] == "message":
                # Store message in thread data
                thread_data["messages"].append(event["data"])
                
            # Send the event to the client
            yield f"data: {json.dumps(event)}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream: {str(e)}")
        # Send error event
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

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
    
    # Initialize state with messages
    state = {"messages": request.messages}
    
    # Return a streaming response
    return StreamingResponse(
        stream_graph_events(
            thread_id=thread_id,
            state=state,
            checkpoint=request.checkpoint,
            command=request.command
        ),
        media_type="text/event-stream"
    )

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