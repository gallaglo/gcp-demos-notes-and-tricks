"""
ADK-based Animation Generation API
Main FastAPI application using ADK agents for animation generation.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from adk import SessionService
from adk.core import Context
from adk_agents import create_animation_workflow_agent, create_conversation_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for required environment variables
if not os.environ.get("BLENDER_SERVICE_URL"):
    logger.warning("BLENDER_SERVICE_URL environment variable is not set.")
    logger.warning("Please set this variable to the URL of your Blender Cloud Run service.")

app = FastAPI(title="ADK Animation Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

# Initialize ADK SessionService
session_service = SessionService()

# Store active sessions (in production, use persistent storage)
active_sessions = {}

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

class Message(BaseModel):
    id: Optional[str] = None
    type: str  # 'human' or 'ai'
    content: str

async def process_with_adk_agent(
    session_id: str, 
    user_message: str, 
    context: Optional[Context] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process user message with ADK agents and stream results.
    
    Args:
        session_id: Unique session identifier
        user_message: User's input message
        context: Optional ADK context for the session
    """
    try:
        # Initialize session if needed
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                "messages": [],
                "status": "initialized",
                "signedUrl": None,
                "context": context or Context()
            }
        
        session_data = active_sessions[session_id]
        
        # Add user message to session
        user_msg = {
            "id": str(uuid4()),
            "type": "human", 
            "content": user_message
        }
        session_data["messages"].append(user_msg)
        
        # Send user message event
        yield {
            "type": "message",
            "data": user_msg
        }
        
        # Update status
        session_data["status"] = "processing"
        yield {
            "type": "status",
            "data": {"status": "Processing your request"}
        }
        
        # First, determine if this is an animation request or conversation
        animation_agent = create_animation_workflow_agent()
        
        # Use the animation planner to analyze the request
        try:
            # Get the first agent (AnimationPlanner) to analyze the request
            planner = animation_agent.agents[0]  # AnimationPlanner
            
            # Process with the planner
            planner_result = await planner.aprocess(user_message, session_data["context"])
            
            logger.info(f"Planner result: {planner_result}")
            
            # Determine next steps based on analysis
            if "generate_animation" in str(planner_result).lower():
                # This is an animation request - use full workflow
                session_data["status"] = "generating_animation"
                yield {
                    "type": "status", 
                    "data": {"status": "Generating your animation"}
                }
                
                # Process with full animation workflow
                workflow_result = await animation_agent.aprocess(user_message, session_data["context"])
                
                # Parse the result to extract components
                result_str = str(workflow_result)
                
                # Look for signed URL in the result
                if "signed_url" in result_str.lower():
                    # Try to extract URL from result
                    import re
                    url_pattern = r'https://[^\s\'"<>]+'
                    urls = re.findall(url_pattern, result_str)
                    
                    if urls:
                        session_data["signedUrl"] = urls[0]
                        session_data["status"] = "completed"
                        
                        yield {
                            "type": "data",
                            "data": {"signed_url": urls[0]}
                        }
                        
                        # Add AI success message
                        ai_msg = {
                            "id": str(uuid4()),
                            "type": "ai",
                            "content": "Your animation is ready! You can see it in the viewer. Is there anything you'd like me to change about it?"
                        }
                        session_data["messages"].append(ai_msg)
                        
                        yield {
                            "type": "message",
                            "data": ai_msg
                        }
                    else:
                        # Animation generated but no URL found
                        ai_msg = {
                            "id": str(uuid4()),
                            "type": "ai", 
                            "content": str(workflow_result)
                        }
                        session_data["messages"].append(ai_msg)
                        
                        yield {
                            "type": "message",
                            "data": ai_msg
                        }
                else:
                    # No signed URL - might be an error or intermediate response
                    ai_msg = {
                        "id": str(uuid4()),
                        "type": "ai",
                        "content": str(workflow_result)
                    }
                    session_data["messages"].append(ai_msg)
                    
                    yield {
                        "type": "message", 
                        "data": ai_msg
                    }
                    
            else:
                # This is a conversation - use conversation agent
                conversation_agent = create_conversation_agent()
                
                session_data["status"] = "conversation"
                yield {
                    "type": "status",
                    "data": {"status": "Having a conversation"}
                }
                
                # Process with conversation agent
                conv_result = await conversation_agent.aprocess(user_message, session_data["context"])
                
                # Add AI response
                ai_msg = {
                    "id": str(uuid4()),
                    "type": "ai",
                    "content": str(conv_result)
                }
                session_data["messages"].append(ai_msg)
                
                yield {
                    "type": "message",
                    "data": ai_msg
                }
        
        except Exception as agent_error:
            logger.error(f"ADK agent error: {str(agent_error)}")
            
            # Fallback to simple response
            ai_msg = {
                "id": str(uuid4()),
                "type": "ai",
                "content": f"I encountered an error processing your request: {str(agent_error)}. Please try again or rephrase your request."
            }
            session_data["messages"].append(ai_msg)
            session_data["status"] = "error"
            
            yield {
                "type": "message",
                "data": ai_msg
            }
            
            yield {
                "type": "error",
                "error": str(agent_error)
            }
        
        # Send final status
        yield {
            "type": "status",
            "data": {"status": session_data["status"].title()}
        }
        
        # End the stream
        yield {
            "type": "end"
        }
        
    except Exception as e:
        logger.error(f"Error in ADK processing: {str(e)}")
        yield {
            "type": "error",
            "error": str(e)
        }

@app.post("/generate")
async def generate_animation(request: AnimationRequest):
    """Legacy endpoint for animation generation - redirects to ADK workflow."""
    try:
        session_id = str(uuid4())
        context = Context()
        
        # Process with ADK agent
        result_events = []
        async for event in process_with_adk_agent(session_id, request.prompt, context):
            result_events.append(event)
        
        # Extract final result
        signed_url = ""
        error = ""
        status = "completed"
        
        for event in result_events:
            if event.get("type") == "data" and "signed_url" in event.get("data", {}):
                signed_url = event["data"]["signed_url"]
            elif event.get("type") == "error":
                error = event.get("error", "")
                status = "error"
        
        return {
            "signed_url": signed_url,
            "generation_status": status,
            "error": error
        }
        
    except Exception as e:
        logger.error(f"Error in generate endpoint: {str(e)}")
        return {
            "signed_url": "",
            "generation_status": "error", 
            "error": str(e)
        }

@app.post("/thread/{thread_id}")
async def handle_thread_request(
    thread_id: str,
    request: ThreadRequest,
    background_tasks: BackgroundTasks
):
    """Handle thread request with ADK agents and SSE streaming."""
    logger.info(f"Received thread request for thread: {thread_id}")
    
    # Create thread ID if not provided
    if thread_id == "new":
        thread_id = str(uuid4())
        logger.info(f"Created new thread with ID: {thread_id}")
    
    # Return streaming response
    return StreamingResponse(
        stream_adk_events(thread_id, request.messages),
        media_type="text/event-stream"
    )

async def stream_adk_events(thread_id: str, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """Generate streaming events for ADK agent processing."""
    try:
        # Extract the latest human message
        latest_message = None
        for msg in messages:
            if msg.get("type") == "human":
                latest_message = msg.get("content")
        
        if not latest_message:
            yield f"data: {json.dumps({'type': 'error', 'error': 'No human message provided'})}\n\n"
            return
        
        # Process with ADK agents
        context = Context()
        async for event in process_with_adk_agent(thread_id, latest_message, context):
            # Format event for SSE
            yield f"data: {json.dumps(event)}\n\n"
            
    except Exception as e:
        logger.error(f"Error in ADK stream: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

@app.get("/thread/{thread_id}")
async def get_thread(thread_id: str):
    """Get the current state of a thread."""
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    
    return active_sessions[thread_id]

@app.options("/{path:path}")
async def preflight_handler(request: Request):
    """Handle preflight OPTIONS requests."""
    return {}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent_framework": "ADK"}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "ADK Animation Generator API",
        "version": "2.0.0",
        "framework": "Google Agent Development Kit (ADK)",
        "endpoints": {
            "generate": "POST /generate - Legacy animation generation",
            "thread": "POST /thread/{thread_id} - Streaming thread-based interaction",
            "health": "GET /health - Health check"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting ADK Animation API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)