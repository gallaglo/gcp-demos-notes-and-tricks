import os
import json
from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from animation_graph import run_animation_generation
from dotenv import load_dotenv
import logging
from typing import Dict, Any, Optional
import google.auth
from google.auth.transport.requests import Request as GAuthRequest
from google.oauth2 import id_token

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnimationRequest(BaseModel):
    prompt: str

class AnimationResponse(BaseModel):
    signed_url: str
    generation_status: str
    error: str = ""

def validate_token(authorization: str = "") -> Optional[str]:
    """Validate the Firebase Auth token in the Authorization header."""
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split("Bearer ")[1]
    return token

def get_auth_info(request: Request) -> Dict[str, Any]:
    """Extract and validate the authorization token from the request."""
    auth_header = request.headers.get("Authorization", "")
    return {"token": validate_token(auth_header)}

@app.post("/generate", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest, auth_info: Dict[str, Any] = Depends(get_auth_info)):
    """Generate a 3D animation from a text prompt"""
    try:
        # Run the LangGraph workflow
        result = run_animation_generation(request.prompt)
        
        # Check for errors
        if result.get("error"):
            raise HTTPException(
                status_code=500, 
                detail=f"Animation generation failed: {result['error']}"
            )
        
        # Return the response
        return AnimationResponse(
            signed_url=result["signed_url"],
            generation_status=result["generation_status"],
            error=""
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error generating animation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))