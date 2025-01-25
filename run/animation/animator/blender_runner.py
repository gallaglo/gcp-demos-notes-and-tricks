import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class BlenderRunner:
    @staticmethod
    def run_blender(script_path: str, output_path: str) -> dict:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            blender_path = "/usr/local/blender/blender"
            cmd = [
                blender_path,
                '--background',
                '--factory-startup',
                '--disable-autoexec',
                '--python', script_path,
                '--',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if any(msg in result.stdout for msg in ["Successfully exported", "Finished glTF 2.0 export"]):
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f'Blender error: {result.stderr}'
                }
        except Exception as e:
            logger.error(f"Error running Blender: {str(e)}")
            return {'success': False, 'error': str(e)}
