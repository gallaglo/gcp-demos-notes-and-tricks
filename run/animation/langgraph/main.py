# main.py - For local testing and development
import os
import json
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from animation_graph import run_animation_generation
from dotenv import load_dotenv
import logging

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

# Add CORS middleware for local development
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

@app.post("/generate", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
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

# Vertex AI compatible endpoint
@app.post("/vertexai")
async def vertex_ai_handler(request: Request):
    """Vertex AI compatible endpoint for Reasoning Engine deployment"""
    try:
        body = await request.json()
        instances = body.get("instances", [])
        
        if not instances or len(instances) == 0:
            raise HTTPException(
                status_code=400,
                detail="No instances provided"
            )
        
        # Get the prompt from the first instance
        prompt = instances[0].get("prompt")
        if not prompt:
            raise HTTPException(
                status_code=400,
                detail="No prompt provided in instance"
            )
        
        # Run the LangGraph workflow
        result = run_animation_generation(prompt)
        
        # Format the response for Vertex AI
        predictions = [{
            "generation_status": result.get("generation_status", "error"),
            "signed_url": result.get("signed_url", ""),
            "error": result.get("error", "")
        }]
        
        return {"predictions": predictions}
    except Exception as e:
        logger.error(f"Error in Vertex AI handler: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)