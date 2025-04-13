import { NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import { fetchWithRetry } from '@/lib/utils';
import { v4 as uuidv4 } from 'uuid';

// Interfaces for type safety
interface AnimationRequest {
  prompt: string;
}

interface AnimationResponse {
  signed_url: string;
  generation_status: string;
  error?: string;
}

// Get ID token for Cloud Run authentication
async function getIdToken(audience: string) {
  try {
    const auth = new GoogleAuth();
    const client = await auth.getIdTokenClient(audience);
    const headers = await client.getRequestHeaders();
    return headers.Authorization.split(' ')[1];
  } catch (error) {
    console.error('Error getting ID token:', error);
    throw new Error('Failed to obtain authentication token');
  }
}

// Get the endpoint from environment at runtime
const getBackendURL = () => {
  // If explicitly set in environment, use that
  if (process.env.LANGGRAPH_ENDPOINT && process.env.LANGGRAPH_ENDPOINT !== "") {
    console.log(`Using configured LANGGRAPH_ENDPOINT: ${process.env.LANGGRAPH_ENDPOINT}`);
    return process.env.LANGGRAPH_ENDPOINT;
  }
  
  // Fallback to relative path for API route
  console.log('Using relative API path: /api/animation');
  return '/api/animation';
};

// Streaming implementation for real-time updates
async function* generateAnimationStream(prompt: string) {
  // Yield initial events
  yield { 
    type: 'status', 
    data: { status: 'initializing', id: uuidv4() } 
  };

  try {
    // Get the backend endpoint and audience URL
    const endpoint = getBackendURL();
    
    // Get authentication token for Cloud Run
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Only get token in production environments and when endpoint is a Cloud Run URL
    if (process.env.NODE_ENV === 'production' && endpoint.includes('.run.app')) {
      const idToken = await getIdToken(endpoint);
      headers['Authorization'] = `Bearer ${idToken}`;
    }

    // Initial request to start generation
    const initialResponse = await fetchWithRetry(
      `${endpoint}/generate`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompt }),
      },
      {
        maxAttempts: 3,
        initialDelay: 2000,
        maxDelay: 10000,
      }
    );

    const data = await initialResponse.json() as AnimationResponse;

    // Validation checks
    if (data.error) {
      yield { 
        type: 'error', 
        data: { 
          error: data.error, 
          id: uuidv4() 
        } 
      };
      return;
    }

    // Stream generation stages
    yield { 
      type: 'status', 
      data: { status: 'generating_script', id: uuidv4() } 
    };

    yield { 
      type: 'message', 
      data: { 
        content: 'Generating animation script...', 
        id: uuidv4() 
      } 
    };

    // Simulate rendering stage (adjust based on actual backend behavior)
    yield { 
      type: 'status', 
      data: { status: 'rendering', id: uuidv4() } 
    };

    yield { 
      type: 'message', 
      data: { 
        content: 'Rendering animation...', 
        id: uuidv4() 
      } 
    };

    // Final data event with signed URL
    yield { 
      type: 'data', 
      data: { 
        signed_url: data.signed_url, 
        id: uuidv4() 
      } 
    };

    // Completion
    yield { 
      type: 'status', 
      data: { status: 'completed', id: uuidv4() } 
    };

    yield { 
      type: 'message', 
      data: { 
        content: 'Animation generation complete!', 
        id: uuidv4() 
      } 
    };

  } catch (error) {
    console.error('Animation generation error:', error);
    yield { 
      type: 'error', 
      data: { 
        error: error instanceof Error ? error.message : 'Unknown error', 
        id: uuidv4() 
      } 
    };
  }
}

// POST handler for direct JSON response
export async function POST(request: Request) {
  try {
    // Parse request body
    const { prompt } = await request.json() as AnimationRequest;
    
    // Validate prompt
    if (!prompt) {
      return NextResponse.json({ error: 'No prompt provided' }, { status: 400 });
    }
    
    // Get the backend endpoint and audience URL
    const endpoint = getBackendURL();
    
    // Setup headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Only get token in production environments and when endpoint is a Cloud Run URL
    if (process.env.NODE_ENV === 'production' && endpoint.includes('.run.app')) {
      const idToken = await getIdToken(endpoint);
      headers['Authorization'] = `Bearer ${idToken}`;
    }

    // Make request to backend service
    const response = await fetchWithRetry(
      `${endpoint}/generate`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompt }),
      },
      {
        maxAttempts: 3,
        initialDelay: 2000,
        maxDelay: 10000,
      }
    );

    // Parse response
    const data = await response.json() as AnimationResponse;
    
    // Error handling
    if (data.error) {
      return NextResponse.json({ error: data.error }, { status: 500 });
    }
    
    // Return successful response
    return NextResponse.json(data);

  } catch (error) {
    console.error('Animation generation error:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Unknown error' 
    }, { status: 500 });
  }
}

// GET handler for streaming events
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const prompt = searchParams.get('prompt');

  if (!prompt) {
    return NextResponse.json({ error: 'No prompt provided' }, { status: 400 });
  }

  // Streaming response
  const encoder = new TextEncoder();
  
  return new Response(
    new ReadableStream({
      async start(controller) {
        try {
          // Create generator for streaming events
          const eventGenerator = generateAnimationStream(prompt);

          // Stream events
          for await (const event of eventGenerator) {
            controller.enqueue(
              encoder.encode(`data: ${JSON.stringify(event)}\n\n`)
            );
          }

          controller.close();
        } catch (error) {
          controller.error(error);
        }
      }
    }),
    {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
      }
    }
  );
}