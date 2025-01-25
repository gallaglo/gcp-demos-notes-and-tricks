import datetime
import logging

logger = logging.getLogger(__name__)

class GCSUploader:
    def __init__(self, bucket):
        self.bucket = bucket
    
    def upload_file(self, local_path: str) -> str:
        try:
            blob_name = f'animations/{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.glb'
            blob = self.bucket.blob(blob_name)
            
            with open(local_path, 'rb') as file_obj:
                blob.upload_from_file(file_obj)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),
                method="GET"
            )
            
            return url
        except Exception as e:
            logger.error(f"Error in GCS operation: {str(e)}")
            raise