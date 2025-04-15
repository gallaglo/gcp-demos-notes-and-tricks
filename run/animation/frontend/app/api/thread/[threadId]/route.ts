import { NextRequest } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import { v4 as uuidv4 } from 'uuid';

// Define MessageType without importing from the client-side hook
interface MessageType {
  id: string;
  type: 'human' | 'ai';
  content: string;
  metadata?: {
    sceneId?: string;
    modifiedObjects?: string[];
    action?: 'create' | 'modify' | 'delete';
  };
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
  const isNewThread = pathParts[pathParts.length - 1] === 'new' 
    ? true 
    : false;
  const threadId = isNewThread 
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
      
      // Send initial state (filtered to exclude the human message we just added)
      const filteredMessages = thread.messages.filter(msg => 
        // Don't include the last human message if it matches our prompt
        !(msg.type === 'human' && msg.content === prompt)
      );

      await writer.write(encoder.encode(
        formatEvent('state', { 
          ...thread, 
          messages: filteredMessages 
        })
      ));
      
      // Update status - analyzing
      thread.status = 'generating_script';
      await writer.write(encoder.encode(formatEvent('status', { status: 'Analyzing your request' })));
      
      // Add AI thinking message - Don't need this anymore, the agent will handle this
      // const thinkingMessageId = uuidv4();
      // const thinkingMessage: MessageType = {
      //   id: thinkingMessageId,
      //   type: 'ai',
      //   content: `I'm generating a 3D animation based on your request: '${prompt}'. This might take a moment...`,
      // };
      // thread.messages.push(thinkingMessage);
      // await writer.write(encoder.encode(formatEvent('message', thinkingMessage)));
      
      // Get the endpoint
      const endpoint = getEndpoint();
      if (!endpoint) {
        throw new Error('Animation service not configured properly');
      }
      
      // Get ID token for Cloud Run
      const idToken = await getIdToken(endpoint);
      
      // Determine if we're creating a new thread or updating an existing one
      const targetThreadId = isNewThread ? 'new' : threadId;
      console.log(`Sending request to ${endpoint}/thread/${targetThreadId} with prompt: ${prompt}`);
      
      // Send request to backend ThreadRequest handler
      const response = await fetch(`${endpoint}/thread/${targetThreadId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          messages: messages,
          checkpoint: null,
          command: null
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Backend error: ${errorText}`);
      }
      
      // Start looking for messages that indicate animation is ready
      await writer.write(encoder.encode(formatEvent('status', { status: 'Rendering animation...' })));
      
      // For streaming response, handle event stream from backend
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Failed to get response reader");
      }
      
      const backendDecoder = new TextDecoder();
      let buffer = "";
      let foundSignedUrl = false;
      let signedUrl = null;
      
      // Process the stream from backend
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += backendDecoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.trim() === '' || !line.startsWith('data: ')) continue;
          
          try {
            // Parse event from backend
            const eventString = line.substring(6);
            const eventData = JSON.parse(eventString);
            
            console.log("Processing event:", eventData.type);
            
            // Forward event to client
            await writer.write(encoder.encode(`data: ${eventString}\n\n`));
            
            // Special handling for data events with signed URLs
            if (eventData.type === 'data' && eventData.data) {
              const url = eventData.data.signed_url || eventData.data.signedUrl;
              if (url) {
                console.log("Found signed URL", url.substring(0, 30) + "...");
                foundSignedUrl = true;
                signedUrl = url;
                thread.signedUrl = url;
                
                // Send an additional explicit data event with the signed URL
                // This ensures the client receives it in a consistent format
                await writer.write(encoder.encode(
                  formatEvent('data', { signed_url: url })
                ));
              }
            }
            
            // Process event for local state
            if (eventData.type === 'message' && eventData.data) {
              const messageData = eventData.data;
              // Add message to thread if it's not already there
              const messageExists = thread.messages.some(msg => 
                (msg.id === messageData.id) || 
                (msg.type === messageData.type && msg.content === messageData.content)
              );
              
              if (!messageExists) {
                thread.messages.push({
                  id: messageData.id || uuidv4(),
                  type: messageData.type,
                  content: messageData.content,
                  metadata: messageData.metadata
                });
              }
            } else if (eventData.type === 'status' && eventData.data?.status) {
              // Update status
              thread.status = eventData.data.status === 'Completed' 
                ? 'completed' 
                : eventData.data.status === 'Conversation'
                  ? 'conversation'
                  : thread.status;
            } else if (eventData.type === 'error') {
              // Update error status
              thread.status = 'error';
            }
          } catch (e) {
            console.error("Failed to parse event from backend:", line, e);
          }
        }
      }
      
      // If we found a signed URL in the events, but the 'data' event might have been missed,
      // send it again to ensure the client receives it
      if (foundSignedUrl && signedUrl) {
        console.log("Sending final signed URL to client");
        await writer.write(encoder.encode(
          formatEvent('data', { signed_url: signedUrl })
        ));
        
        // Success messages are now handled by the agent, so we don't need to add them here
        
        thread.status = 'completed';
        await writer.write(encoder.encode(formatEvent('status', { status: 'Completed' })));
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
  // Include the threadId in the Location header for new threads
  return new Response(stream.readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'Location': isNewThread ? `/api/thread/${threadId}` : url.pathname,
      'X-Thread-ID': threadId  // Add thread ID explicitly in header for client reference
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

// DELETE endpoint to clear a thread
export async function DELETE(request: NextRequest) {
  // Extract threadId from URL
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/');
  const threadId = pathParts[pathParts.length - 1];
  
  if (threadId === 'all') {
    // Clear all threads - can be useful for admin/debugging
    Object.keys(activeThreads).forEach(key => {
      delete activeThreads[key];
    });
    
    return new Response(JSON.stringify({ success: true, message: 'All threads cleared' }), {
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
  
  if (!activeThreads[threadId]) {
    return new Response(JSON.stringify({ error: 'Thread not found' }), {
      status: 404,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
  
  // Delete this specific thread
  delete activeThreads[threadId];
  
  return new Response(JSON.stringify({ success: true }), {
    headers: {
      'Content-Type': 'application/json',
    },
  });
}