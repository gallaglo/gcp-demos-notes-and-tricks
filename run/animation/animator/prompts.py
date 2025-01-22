# LangChain prompt templates
from langchain.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are a specialized AI that generates 3D animation scripts for Blender. 
You must follow the exact patterns and requirements provided. Your output will be used to generate
a GLB/GLTF animation file."""

HUMAN_PROMPT = """Create a Blender animation based on this description:
{user_prompt}

Remember:
- Frame range must be 1-250 (10 seconds at 25fps)
- Camera must be properly positioned and rotated
- Scene must include proper lighting
- All objects must use the standard primitive creation methods
- Animations must use keyframe insertion
- Materials must follow the node-based setup pattern
"""

blender_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", HUMAN_PROMPT)
])