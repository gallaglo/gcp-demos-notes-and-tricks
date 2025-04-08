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
  status: 'initialized' | 'generating_script' | 'rendering' | 'completed' | 'error' | 'conversation';
  signedUrl: string | null;
}

// In-memory store for active threads (will be lost on server restart)
// In production, you might want to use Redis or another external store
const activeThreads: Record<string, ThreadData> = {};

// Safe handling of environment variables for build time
const getEndpoint = () => {
  // Check if we have a configured endpoint
  if (process.env.LANGGRAPH_ENDPOINT && process.env.LANGGRAPH_ENDPOINT !== '') {
    return process.env.LANGGRAPH_ENDPOINT;
  }
  
  // No endpoint configured
  return '';
};

async function getIdToken(audience: string) {
  const auth = new GoogleAuth();
  const client = await auth.getIdTokenClient(audience);
  const headers = await client.getRequestHeaders();
  return headers.Authorization.split(' ')[1];
}

// Helper function to send event to client
function formatEvent<T>(type: string, data: T): string {
  return `data: ${JSON.stringify({ type, data })}\n\n`;
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
      await writer.write(encoder.encode(formatEvent('state', thread)));
      
      // Update status - analyzing
      thread.status = 'generating_script';
      await writer.write(encoder.encode(formatEvent('status', { status: 'Analyzing your request' })));
      
      // Add AI thinking message
      const thinkingMessageId = uuidv4();
      const thinkingMessage: MessageType = {
        id: thinkingMessageId,
        type: 'ai',
        content: `I'm generating a 3D animation based on your request: '${prompt}'. This might take a moment...`,
      };
      thread.messages.push(thinkingMessage);
      await writer.write(encoder.encode(formatEvent('message', thinkingMessage)));
      
      // Get the endpoint
      const endpoint = getEndpoint();
      if (!endpoint) {
        throw new Error('Animation service not configured properly');
      }
      
      // Get ID token for Cloud Run
      const idToken = await getIdToken(endpoint);
      
      // Send request to LangGraph service
      console.log(`Sending request to ${endpoint}/generate with prompt: ${prompt}`);
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
      
      const result = await response.json();
      console.log("Received response:", JSON.stringify(result, null, 2));
      
      if (result.error) {
        throw new Error(result.error);
      }
      
      // Update status based on result
      if (result.generation_status === 'completed' && result.signed_url) {
        // Set the signed URL in thread data
        thread.signedUrl = result.signed_url;
        
        // IMPORTANT: Send the data event with signed_url in the correct format
        // This matches what useAnimationStream.ts expects
        await writer.write(encoder.encode(
          formatEvent('data', { signed_url: result.signed_url })
        ));
        
        // Add success message
        const successMessage: MessageType = {
          id: uuidv4(),
          type: 'ai',
          content: "Your animation is ready! You can see it in the viewer. Is there anything you'd like me to change about it?",
        };
        thread.messages.push(successMessage);
        await writer.write(encoder.encode(formatEvent('message', successMessage)));
        
        // Update status
        thread.status = 'completed';
        await writer.write(encoder.encode(formatEvent('status', { status: 'Completed' })));
      } else {
        // This was just a conversation or there was an issue
        if (result.history && Array.isArray(result.history)) {
          // Add AI messages from history
          for (const msg of result.history) {
            if (msg.role === 'ai') {
              const aiMessage: MessageType = {
                id: uuidv4(),
                type: 'ai',
                content: msg.content,
              };
              thread.messages.push(aiMessage);
              await writer.write(encoder.encode(formatEvent('message', aiMessage)));
            }
          }
        }
        
        // If no signed URL, this was just a conversation
        thread.status = 'conversation';
        await writer.write(encoder.encode(formatEvent('status', { status: 'Conversation' })));
      }
      
      // End the stream
      await writer.write(encoder.encode(formatEvent('end', {})));
    } catch (error) {
      console.error('Error in animation generation:', error);
      
      // Send error message
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      
      await writer.write(encoder.encode(formatEvent('error', { error: errorMessage })));
      
      // Add error message to thread
      const thread = activeThreads[threadId];
      if (thread) {
        const aiErrorMessage: MessageType = {
          id: uuidv4(),
          type: 'ai',
          content: `Error: ${errorMessage}`,
        };
        thread.messages.push(aiErrorMessage);
        await writer.write(encoder.encode(formatEvent('message', aiErrorMessage)));
        
        thread.status = 'error';
      }
      
      // End the stream
      await writer.write(encoder.encode(formatEvent('end', {})));
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