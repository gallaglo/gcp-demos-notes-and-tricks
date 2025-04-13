import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from animation_graph import run_animation_generation, generate_blender_script, render_animation, AnimationState, Message
from scene_manager import SceneManager
from prompts import format_mcp_edit_prompt
from dotenv import load_dotenv
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
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
    allow_methods=["GET", "POST", "OPTIONS", "PUT"],
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

# Initialize scene manager
scene_manager = SceneManager()

# Store active threads (in-memory storage - not persistent)
active_threads = {}

class AnimationRequest(BaseModel):
    prompt: str
    thread_id: Optional[str] = None

class AnimationResponse(BaseModel):
    signed_url: str
    generation_status: str
    error: str = ""
    scene_id: Optional[str] = None
    scene_state: Optional[Dict[str, Any]] = None

class ThreadRequest(BaseModel):
    messages: List[Dict[str, Any]]
    checkpoint: Optional[str] = None
    command: Optional[Dict[str, Any]] = None

class SceneEditRequest(BaseModel):
    prompt: str
    scene_state: Dict[str, Any]
    thread_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None

@app.post("/generate")
async def generate_animation(request: AnimationRequest):
    """Endpoint to generate an animation from a prompt."""
    logger.info(f"Received animation request with prompt: {request.prompt}")
    try:
        # Get thread ID from request if available
        thread_id = request.thread_id if request.thread_id else None
        
        result = run_animation_generation(request.prompt, thread_id=thread_id)
        logger.info(f"Animation generation completed with result: {result}")
        
        # Get scene state information if available
        scene_info = {}
        if result.get("thread_id") and result.get("scene_state"):
            scene_info = {
                "scene_id": result.get("scene_state", {}).get("id", ""),
                "scene_state": result.get("scene_state", {})
            }
        
        # Ensure consistent response structure
        return {
            "signed_url": result.get("signed_url", ""),
            "generation_status": result.get("generation_status", ""),
            "error": result.get("error", ""),
            "history": result.get("history", []),
            "is_modification": result.get("is_modification", False),
            **scene_info  # Include scene information if available
        }
    except Exception as e:
        logger.error(f"Error in animation generation: {str(e)}")
        return {
            "signed_url": "",
            "generation_status": "error",
            "error": str(e)
        }

@app.post("/analyze-edit")
async def analyze_edit_request(request: SceneEditRequest):
    """
    Analyze an edit request using MCP to determine specific changes to the scene.
    
    This endpoint takes a user prompt, current scene state, and conversation history,
    and uses the Model Context Protocol to parse specific editing instructions.
    """
    try:
        # Format the prompt using MCP
        mcp_prompt = format_mcp_edit_prompt(
            request.scene_state, 
            request.conversation_history or [], 
            request.prompt
        )
        
        # Get LLM for analysis
        from animation_graph import get_llm
        llm = get_llm("gemini-2.0-pro-001")  # Use more capable model for parsing
        
        # Send request to LLM
        response = llm.invoke(mcp_prompt)
        
        # Extract JSON from response
        raw_content = response.content.strip()
        
        # Extract the JSON part if wrapped in ```json or ```
        if "```json" in raw_content:
            json_text = raw_content.split("```json")[1].split("```")[0]
        elif "```" in raw_content:
            json_text = raw_content.split("```")[1].split("```")[0]
        else:
            json_text = raw_content
        
        # Parse the edit instructions
        edit_instructions = json.loads(json_text)
        
        return {
            "success": True,
            "edit_instructions": edit_instructions
        }
    except Exception as e:
        logger.error(f"Error analyzing edit request: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/scene-history/{thread_id}")
async def get_scene_history(thread_id: str):
    """Get the scene history for a thread"""
    try:
        # Get scene history from scene manager
        scene_history = scene_manager.get_thread_scene_history(thread_id)
        
        return {
            "success": True,
            "thread_id": thread_id,
            "history": scene_history
        }
    except Exception as e:
        logger.error(f"Error getting scene history: {str(e)}")
        return {
            "success": False,
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
        
        # Run the animation generation with history and thread_id
        result = run_animation_generation(latest_message, history, thread_id)
        
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
                
                # Include scene state info in the event if available
                scene_data = {"signed_url": result["signed_url"]}
                if result.get("scene_state"):
                    scene_data["scene_id"] = result.get("scene_state", {}).get("id", "")
                    
                    # Send scene state event
                    yield {
                        "type": "scene_state",
                        "data": {"scene_state": result.get("scene_state")}
                    }
                
                yield {
                    "type": "data",
                    "data": scene_data
                }
                
                yield {
                    "type": "status",
                    "data": {"status": "Completed"}
                }
                
                # Send scene history if available
                if thread_id:
                    scene_history = scene_manager.get_thread_scene_history(thread_id)
                    if scene_history:
                        yield {
                            "type": "scene_history",
                            "data": {"scene_history": scene_history}
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
    
    # Get thread data
    thread_data = active_threads[thread_id]
    
    # Get scene state if available
    current_scene = scene_manager.get_current_scene_for_thread(thread_id)
    if current_scene:
        thread_data["sceneState"] = current_scene
    
    # Get scene history if available
    scene_history = scene_manager.get_thread_scene_history(thread_id)
    if scene_history:
        thread_data["sceneHistory"] = scene_history
    
    return thread_data

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