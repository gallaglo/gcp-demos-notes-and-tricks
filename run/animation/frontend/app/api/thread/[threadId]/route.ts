import { NextRequest } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import { v4 as uuidv4 } from 'uuid';

// Define MessageType without importing from the client-side hook
interface MessageType {
  id: string;
  type: 'human' | 'ai';
  content: string;
}

// Define thread data interface
interface ThreadData {
  messages: MessageType[];
  status: 'initialized' | 'generating_script' | 'rendering' | 'completed' | 'error';
  signedUrl: string | null;
}

// In-memory store for active threads (will be lost on server restart)
// In production, you might want to use Redis or another external store
const activeThreads: Record<string, ThreadData> = {};

// Safe handling of environment variables for build time
const getEndpoint = () => {
  return process.env.LANGGRAPH_ENDPOINT || '';
};

async function getIdToken(audience: string) {
  const auth = new GoogleAuth();
  const client = await auth.getIdTokenClient(audience);
  const headers = await client.getRequestHeaders();
  return headers.Authorization.split(' ')[1];
}

// POST handler for thread generation
export async function POST(request: NextRequest) {
  // Extract threadId from URL
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/');
  const threadId = pathParts[pathParts.length - 1] === 'new' 
    ? uuidv4() 
    : pathParts[pathParts.length - 1];
  
  // Initialize response stream
  const encoder = new TextEncoder();
  const stream = new TransformStream();
  const writer = stream.writable.getWriter();
  
  // Helper function to send event to the client
  const sendEvent = async (event: string, data: unknown) => {
    await writer.write(
      encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
    );
  };
  
  // Process the request body
  const body = await request.json();
  const { messages } = body;
  
  // Extract prompt from the last human message
  let prompt = '';
  if (Array.isArray(messages)) {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].type === 'human') {
        prompt = messages[i].content;
        break;
      }
    }
  }
  
  // Process in background
  (async () => {
    try {
      // Initialize or get thread data
      if (!activeThreads[threadId]) {
        activeThreads[threadId] = {
          messages: [],
          status: 'initialized',
          signedUrl: null,
        };
      }
      
      const thread = activeThreads[threadId];
      
      // Add the human message to the thread
      if (prompt) {
        const humanMessage: MessageType = {
          id: uuidv4(),
          type: 'human',
          content: prompt,
        };
        thread.messages.push(humanMessage);
      }
      
      // Send initial state
      await sendEvent('state', thread);
      
      // Add AI thinking message
      const thinkingMessageId = uuidv4();
      const thinkingMessage: MessageType = {
        id: thinkingMessageId,
        type: 'ai',
        content: `Starting to generate animation for: ${prompt}`,
      };
      thread.messages.push(thinkingMessage);
      await sendEvent('message', thinkingMessage);
      
      // Get the endpoint
      const endpoint = getEndpoint();
      if (!endpoint) {
        throw new Error('Animation service not configured properly');
      }
      
      // Get ID token for Cloud Run
      const idToken = await getIdToken(endpoint);
      
      // Update status - generating script
      thread.status = 'generating_script';
      await sendEvent('status', { status: 'Generating Blender script' });
      
      // Send request to LangGraph service
      const response = await fetch(`${endpoint}/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Backend error: ${errorText}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Update status - rendering
      thread.status = 'rendering';
      await sendEvent('status', { status: 'Rendering animation' });
      
      // Add rendering message
      const renderingMessage: MessageType = {
        id: uuidv4(),
        type: 'ai',
        content: 'Script generated successfully. Rendering animation...',
      };
      thread.messages.push(renderingMessage);
      await sendEvent('message', renderingMessage);
      
      // Wait for rendering to complete (simulated with timeout in this example)
      // In a real implementation, you might poll for updates or use websockets
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      if (data.generation_status !== 'completed') {
        throw new Error('Animation generation failed');
      }
      
      if (!data.signed_url) {
        throw new Error('No signed URL in response');
      }
      
      // Update with the signed URL
      thread.signedUrl = data.signed_url;
      await sendEvent('data', { signed_url: data.signed_url });
      
      // Add completion message
      const completionMessage: MessageType = {
        id: uuidv4(),
        type: 'ai',
        content: 'Your animation is ready! You can view and download it now.',
      };
      thread.messages.push(completionMessage);
      await sendEvent('message', completionMessage);
      
      // Update status - completed
      thread.status = 'completed';
      await sendEvent('status', { status: 'Completed' });
      
      // End the stream
      await sendEvent('end', {});
    } catch (error) {
      console.error('Error in animation generation:', error);
      
      // Send error message
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      
      await sendEvent('error', { error: errorMessage });
      
      // Add error message to thread
      const thread = activeThreads[threadId];
      if (thread) {
        const aiErrorMessage: MessageType = {
          id: uuidv4(),
          type: 'ai',
          content: `Error: ${errorMessage}`,
        };
        thread.messages.push(aiErrorMessage);
        await sendEvent('message', aiErrorMessage);
        
        thread.status = 'error';
      }
    } finally {
      writer.close();
    }
  })().catch(console.error);
  
  // Return the stream response
  return new Response(stream.readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
    },
  });
}

// Simple GET to retrieve thread state
export async function GET(request: NextRequest) {
  // Extract threadId from URL
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/');
  const threadId = pathParts[pathParts.length - 1];
  
  if (!activeThreads[threadId]) {
    return new Response(JSON.stringify({ error: 'Thread not found' }), {
      status: 404,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
  
  return new Response(JSON.stringify(activeThreads[threadId]), {
    headers: {
      'Content-Type': 'application/json',
    },
  });
}