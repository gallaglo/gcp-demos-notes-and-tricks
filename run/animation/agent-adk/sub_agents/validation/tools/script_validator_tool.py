"""Advanced Blender Script Validation Tool for ADK Animation Agent"""
import re
import ast
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class AdvancedBlenderScriptValidator:
    """Enhanced Blender script validator with comprehensive security and correctness checks."""
    
    def __init__(self):
        self.forbidden_terms = [
            'subprocess', 'os.system', 'eval(', 'exec(', '__import__',
            'open(', 'file(', 'input(', 'raw_input(', 
            'requests.', 'urllib', 'socket', 'http',
            'sys.exit', 'quit(', 'exit(',
            'pickle.', 'marshal.', 'shelve.'
        ]
        
        self.required_imports = [
            'import bpy',
            'import sys', 
            'import math'
        ]
        
        self.required_components = [
            'bpy.ops.export_scene.gltf(',
            'filepath=output_path',
            'export_format=\'GLB\'',
            'sys.argv'
        ]
        
        self.blender_api_patterns = {
            'object_creation': [
                r'bpy\.ops\.mesh\.primitive_\w+_add\(',
                r'bpy\.data\.objects\.new\(',
                r'bpy\.context\.scene\.collection\.objects\.link\('
            ],
            'camera_setup': [
                r'bpy\.data\.cameras\.new\(',
                r'bpy\.context\.scene\.camera\s*='
            ],
            'lighting': [
                r'bpy\.data\.lights\.new\(',
                r'type=[\'"]SUN[\'"]'
            ],
            'animation': [
                r'\.keyframe_insert\(',
                r'bpy\.context\.scene\.frame_\w+\s*='
            ]
        }
    
    def validate_script(self, script: str) -> Dict[str, Any]:
        """
        Comprehensive validation of Blender script.
        
        Args:
            script (str): The Blender Python script to validate
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'security_issues': [],
            'missing_components': [],
            'syntax_issues': [],
            'recommendations': []
        }
        
        try:
            # Security validation
            security_results = self._validate_security(script)
            validation_results.update(security_results)
            
            # Syntax validation
            syntax_results = self._validate_syntax(script)
            validation_results.update(syntax_results)
            
            # Required components validation
            components_results = self._validate_required_components(script)
            validation_results.update(components_results)
            
            # Blender API usage validation
            api_results = self._validate_blender_api_usage(script)
            validation_results.update(api_results)
            
            # Common issues validation
            issues_results = self._validate_common_issues(script)
            validation_results.update(issues_results)
            
            # Overall validation status
            validation_results['valid'] = (
                len(validation_results['errors']) == 0 and 
                len(validation_results['security_issues']) == 0 and
                len(validation_results['missing_components']) == 0
            )
            
            # Generate summary
            validation_results['summary'] = self._generate_validation_summary(validation_results)
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            validation_results.update({
                'valid': False,
                'errors': [f'Validation process failed: {str(e)}']
            })
        
        return validation_results
    
    def _validate_security(self, script: str) -> Dict[str, List[str]]:
        """Check for security vulnerabilities."""
        security_issues = []
        
        for term in self.forbidden_terms:
            if term in script:
                security_issues.append(f'Forbidden term detected: {term}')
        
        # Check for potential code injection patterns
        injection_patterns = [
            r'exec\s*\(',
            r'eval\s*\(',
            r'__import__\s*\(',
            r'getattr\s*\(',
            r'setattr\s*\(',
            r'globals\s*\(',
            r'locals\s*\('
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, script):
                security_issues.append(f'Potential code injection pattern: {pattern}')
        
        return {'security_issues': security_issues}
    
    def _validate_syntax(self, script: str) -> Dict[str, List[str]]:
        """Validate Python syntax."""
        syntax_issues = []
        
        try:
            ast.parse(script)
        except SyntaxError as e:
            syntax_issues.append(f'Python syntax error: {str(e)} at line {e.lineno}')
        except Exception as e:
            syntax_issues.append(f'Script parsing error: {str(e)}')
        
        return {'syntax_issues': syntax_issues}
    
    def _validate_required_components(self, script: str) -> Dict[str, List[str]]:
        """Check for required Blender script components."""
        missing_components = []
        
        # Check required imports
        for import_stmt in self.required_imports:
            if import_stmt not in script:
                missing_components.append(f'Missing required import: {import_stmt}')
        
        # Check required components
        for component in self.required_components:
            if component not in script:
                missing_components.append(f'Missing required component: {component}')
        
        # Check for command line argument handling
        if 'sys.argv.index("--")' not in script:
            missing_components.append('Missing proper command line argument handling')
        
        return {'missing_components': missing_components}
    
    def _validate_blender_api_usage(self, script: str) -> Dict[str, List[str]]:
        """Validate proper Blender API usage."""
        warnings = []
        recommendations = []
        
        # Check for proper object creation patterns
        if 'bpy.data.objects.new(' in script:
            # Check for incorrect object creation syntax
            pattern = r'bpy\.data\.objects\.new\([\'"][^\'"]+[\'"],\s*[\'"][^\'"]+[\'"],\s*[^)]+\)'
            matches = re.findall(pattern, script)
            if matches:
                warnings.append('Incorrect object creation syntax detected - too many arguments')
        
        # Check for camera setup
        camera_patterns_found = sum(1 for pattern in self.blender_api_patterns['camera_setup'] 
                                   if re.search(pattern, script))
        if camera_patterns_found == 0:
            warnings.append('No camera setup detected - animation may not render properly')
        
        # Check for lighting setup
        lighting_patterns_found = sum(1 for pattern in self.blender_api_patterns['lighting']
                                     if re.search(pattern, script))
        if lighting_patterns_found == 0:
            warnings.append('No lighting setup detected - animation may appear dark')
        
        # Check for animation keyframes
        if '.keyframe_insert(' not in script:
            warnings.append('No keyframe animation detected - this may be a static scene')
        
        # Check for scene cleanup
        if 'bpy.ops.object.select_all' not in script or 'bpy.ops.object.delete' not in script:
            recommendations.append('Consider adding scene cleanup at the beginning of the script')
        
        return {'warnings': warnings, 'recommendations': recommendations}
    
    def _validate_common_issues(self, script: str) -> Dict[str, List[str]]:
        """Check for common Blender scripting issues."""
        errors = []
        warnings = []
        
        # Check for old-style object linking (common error)
        if 'bpy.context.scene.objects.link(' in script:
            errors.append('Old-style object linking detected - use bpy.context.scene.collection.objects.link()')
        
        # Check for rotation property usage
        if 'obj.rotation =' in script:
            warnings.append('Using obj.rotation - consider using obj.rotation_euler for clarity')
        
        # Check for frame range setup
        if 'frame_start' not in script or 'frame_end' not in script:
            warnings.append('Frame range not explicitly set - animation duration may be unexpected')
        
        # Check for material setup
        if 'bpy.data.materials.new(' in script:
            if 'use_nodes = True' not in script:
                warnings.append('Material created but node system not enabled')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _generate_validation_summary(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable validation summary."""
        summary_parts = []
        
        if results['valid']:
            summary_parts.append("✅ Script validation passed")
        else:
            summary_parts.append("❌ Script validation failed")
        
        error_count = len(results['errors']) + len(results['security_issues']) + len(results['missing_components'])
        if error_count > 0:
            summary_parts.append(f"🚨 {error_count} critical issues found")
        
        warning_count = len(results['warnings'])
        if warning_count > 0:
            summary_parts.append(f"⚠️ {warning_count} warnings")
        
        recommendation_count = len(results['recommendations'])
        if recommendation_count > 0:
            summary_parts.append(f"💡 {recommendation_count} recommendations")
        
        return " | ".join(summary_parts)

async def validate_blender_script( script: str) -> Dict[str, Any]:
    """
    Comprehensive validation of a Blender Python script.
    
    Args:
        script: The Blender Python script to validate
        
    Returns:
        Dictionary containing detailed validation results
    """
    try:
        validator = AdvancedBlenderScriptValidator()
        validation_results = validator.validate_script(script)
        
        # Store validation results in tool context state
        
        return {
            "status": "completed",
            "valid": validation_results["valid"],
            "summary": validation_results["summary"],
            "error_count": len(validation_results["errors"]) + len(validation_results["security_issues"]),
            "warning_count": len(validation_results["warnings"]),
            "details": validation_results,
            "message": "Script validation completed"
        }
        
    except Exception as e:
        error_msg = f"Script validation failed: {str(e)}"
        logger.error(error_msg)
        
        # Store error in tool context state
        
        return {
            "status": "error",
            "valid": False,
            "summary": "❌ Validation process failed",
            "error": error_msg,
            "message": "Failed to validate script"
        }

async def fix_common_script_issues( script: str) -> Dict[str, Any]:
    """
    Automatically fix common Blender script issues.
    
    Args:
        script: The original Blender script
        
    Returns:
        Dictionary containing fixed script and applied fixes
    """
    try:
        applied_fixes = []
        fixed_script = script
        
        # Fix camera creation with wrong number of arguments
        old_pattern = r'bpy\.data\.objects\.new\("Camera",\s*"Camera",\s*([^)]+)\)'
        new_pattern = r'bpy.data.objects.new("Camera", \1)'
        if re.search(old_pattern, fixed_script):
            fixed_script = re.sub(old_pattern, new_pattern, fixed_script)
            applied_fixes.append("Fixed camera object creation syntax")
        
        # Fix light object creation
        light_patterns = [
            (r'bpy\.data\.objects\.new\("([^"]*Light[^"]*)",\s*"[^"]*Light[^"]*",\s*([^)]+)\)', 
             r'bpy.data.objects.new("\1", \2)'),
            (r'bpy\.data\.objects\.new\("Sun",\s*"Sun",\s*([^)]+)\)',
             r'bpy.data.objects.new("Sun", \1)')
        ]
        
        for old_pat, new_pat in light_patterns:
            if re.search(old_pat, fixed_script):
                fixed_script = re.sub(old_pat, new_pat, fixed_script)
                applied_fixes.append("Fixed light object creation syntax")
        
        # Fix rotation property usage
        if 'obj.rotation = (' in fixed_script:
            fixed_script = fixed_script.replace('obj.rotation = (', 'obj.rotation_euler = (')
            applied_fixes.append("Fixed rotation property usage")
        
        # Fix old-style object linking
        if 'bpy.context.scene.objects.link(' in fixed_script:
            fixed_script = fixed_script.replace(
                'bpy.context.scene.objects.link(',
                'bpy.context.scene.collection.objects.link('
            )
            applied_fixes.append("Fixed old-style object linking")
        
        # Store fixed script in tool context state
        
        return {
            "status": "completed",
            "script": fixed_script,
            "applied_fixes": applied_fixes,
            "fix_count": len(applied_fixes),
            "message": f"Applied {len(applied_fixes)} automatic fixes"
        }
        
    except Exception as e:
        error_msg = f"Script fixing failed: {str(e)}"
        logger.error(error_msg)
        
        
        return {
            "status": "error",
            "script": script,  # Return original script
            "applied_fixes": [],
            "error": error_msg,
            "message": "Failed to apply automatic fixes"
        }

async def get_validation_status() -> Dict[str, Any]:
    """
    Get the current validation status from tool context state.
    
    Args:
        
    Returns:
        Dictionary containing validation status information
    """
    return {
        "validation_status": "not_started",
        "valid": False,
        "error": "",
        "has_result": False
    }