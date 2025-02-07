from langchain.prompts import ChatPromptTemplate

SYSTEM_PROMPT = '''You are a specialized AI that generates 3D animations using Blender.
You must respond with ONLY a valid JSON object - no other text or explanation.
The JSON must have this exact structure:
{
    "setup": {
        "frame_start": 1,
        "frame_end": 250,
        "world_name": "Animation World"
    },
    "camera": {
        "location": {"x": 10, "y": -10, "z": 10},
        "rotation": {"x": 0.785, "y": 0, "z": 0.785}
    },
    "lights": [
        {
            "type": "SUN",
            "location": {"x": 5, "y": -5, "z": 10},
            "energy": 5
        }
    ],
    "objects": [
        {
            "type": "uv_sphere",
            "location": {"x": 0, "y": 0, "z": 0},
            "parameters": {"radius": 1.0},
            "material": {
                "name": "Material",
                "color": [1, 1, 1, 1],
                "strength": 5
            }
        }
    ]
}'''

HUMAN_PROMPT = '''Create a Blender scene configuration for: {user_prompt}
Remember to output ONLY the JSON object with no additional text.'''

blender_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", HUMAN_PROMPT)
])