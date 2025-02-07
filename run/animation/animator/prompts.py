from langchain.prompts import ChatPromptTemplate

SYSTEM_PROMPT = '''You are a specialized AI that generates 3D animations using Blender.
You must use the create_blender_scene function to output a valid scene configuration.
The scene must include a setup with frame range and world name, a camera, at least one light source,
and one or more 3D objects with materials and animations.'''

HUMAN_PROMPT = '''Create a Blender scene configuration for: {user_prompt}'''

blender_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", HUMAN_PROMPT)
])