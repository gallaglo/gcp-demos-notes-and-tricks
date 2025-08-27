"""GCS Upload Tool for ADK Animation Agent"""
import uuid
import datetime
import logging
from typing import Dict, Any
from google.cloud import storage
from google.adk.tools import tool
from google.adk.tools.context import ToolContext

logger = logging.getLogger(__name__)

class GCSUploader:
    """Handles Google Cloud Storage operations for animation files."""
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def upload_file_with_script(self, animation_path: str, script_content: str) -> str:
        """
        Uploads both animation and script files to GCS and returns animation signed URL.
        
        Args:
            animation_path (str): Path to the local animation file
            script_content (str): Content of the Blender script
            
        Returns:
            str: Signed URL for downloading the animation file
            
        Raises:
            Exception: If upload or URL generation fails
        """
        try:
            # Generate a unique folder name for this animation set
            folder_id = str(uuid.uuid4())
            base_path = f'animations/{folder_id}'
            
            # Upload animation
            animation_blob_name = f'{base_path}/animation.glb'
            animation_blob = self.bucket.blob(animation_blob_name)
            with open(animation_path, 'rb') as file_obj:
                animation_blob.upload_from_file(file_obj)
            logger.info(f"Successfully uploaded animation to {animation_blob_name}")
            
            # Upload script (for debugging purposes)
            script_blob_name = f'{base_path}/script.py'
            script_blob = self.bucket.blob(script_blob_name)
            script_blob.upload_from_string(script_content)
            logger.info(f"Successfully uploaded script to {script_blob_name}")
            
            # Generate signed URL only for animation
            url = animation_blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),
                method="GET",
            )
            
            logger.info(f"Generated signed URL for animation in {base_path}")
            return url
            
        except Exception as e:
            logger.error(f"Error in GCS operation: {str(e)}")
            raise

@tool
async def upload_animation_to_gcs(tool_context: ToolContext, animation_path: str, script_content: str, bucket_name: str) -> Dict[str, Any]:
    """
    Tool to upload animation and script files to Google Cloud Storage.
    
    Args:
        tool_context: ADK tool context
        animation_path: Path to the animation file to upload
        script_content: Content of the Blender script used to generate the animation
        bucket_name: Name of the GCS bucket to upload to
        
    Returns:
        Dictionary containing signed URL and upload status
    """
    try:
        uploader = GCSUploader(bucket_name)
        signed_url = uploader.upload_file_with_script(animation_path, script_content)
        
        # Store results in tool context state
        tool_context.state["signed_url"] = signed_url
        tool_context.state["upload_status"] = "success"
        
        return {
            "status": "success",
            "signed_url": signed_url,
            "expiration": "15 minutes",
            "message": "Animation successfully uploaded to cloud storage"
        }
        
    except Exception as e:
        error_msg = f"Failed to upload animation: {str(e)}"
        logger.error(error_msg)
        
        # Store error in tool context state
        tool_context.state["upload_status"] = "error"
        tool_context.state["upload_error"] = error_msg
        
        return {
            "status": "error",
            "error": error_msg,
            "signed_url": "",
            "message": "Failed to upload animation to cloud storage"
        }

@tool
async def get_storage_status(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool to get the current storage upload status.
    
    Args:
        tool_context: ADK tool context
        
    Returns:
        Dictionary containing current storage status
    """
    upload_status = tool_context.state.get("upload_status", "not_started")
    signed_url = tool_context.state.get("signed_url", "")
    upload_error = tool_context.state.get("upload_error", "")
    
    return {
        "upload_status": upload_status,
        "signed_url": signed_url,
        "error": upload_error,
        "has_result": bool(signed_url)
    }