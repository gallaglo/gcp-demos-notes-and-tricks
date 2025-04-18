import { NextResponse } from 'next/server';

// Helper function to get our MCP server endpoint
const getMcpEndpoint = () => {
  return process.env.ANIMATION_MCP_URL || 'http://localhost:8000';
};

export async function POST(request: Request) {
  try {
    // Parse the request body
    const { messages } = await request.json();
    
    // Get the last user message
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
    if (!lastUserMessage) {
      return NextResponse.json({ error: 'No user message found' }, { status: 400 });
    }
    
    // Check if this is an animation request
    const isAnimationRequest = lastUserMessage.content.toLowerCase().includes('creat') || 
                              lastUserMessage.content.toLowerCase().includes('generat') ||
                              lastUserMessage.content.toLowerCase().includes('animat') ||
                              lastUserMessage.content.toLowerCase().includes('make');
    
    if (isAnimationRequest) {
      // Call the MCP server with the animation prompt
      const mcpResponse = await fetch(`${getMcpEndpoint()}/api/tools/generate_animation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: lastUserMessage.content,
        }),
      });
      
      if (!mcpResponse.ok) {
        throw new Error(`MCP server error: ${mcpResponse.statusText}`);
      }
      
      const animationResult = await mcpResponse.json();
      
      // Format a response to add to the chat
      const assistantMessage = {
        role: 'assistant',
        content: `I've created your animation! You can see it in the viewer panel. ${
          animationResult.message || 'Let me know if you want any changes.'
        }`
      };
      
      return NextResponse.json({
        messages: [assistantMessage],
        animation: {
          signed_url: animationResult.signed_url,
          status: animationResult.status
        }
      });
    } else {
      // Regular chat conversation - no animation needed
      // You could call a different MCP endpoint for chat, or use another AI service
      const assistantMessage = {
        role: 'assistant',
        content: "I can help you create 3D animations! Just describe what you'd like to see animated, and I'll generate it for you."
      };
      
      return NextResponse.json({
        messages: [assistantMessage],
      });
    }
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { 
        error: error instanceof Error ? error.message : 'Unknown error',
        messages: [{
          role: 'assistant',
          content: 'Sorry, there was an error processing your request. Please try again.'
        }]
      }, 
      { status: 500 }
    );
  }
}