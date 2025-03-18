import { NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import { fetchWithRetry } from '@/lib/utils';

// Safe handling of environment variables for build time
// We use an empty string as default for build, but check at runtime
const getEndpoint = () => {
  return process.env.LANGGRAPH_ENDPOINT || '';
};

interface AnimationRequest {
  prompt: string;
}

interface AnimationResponse {
  signed_url: string;
  generation_status: string;
  error?: string;
}

async function getIdToken(audience: string) {
  const auth = new GoogleAuth();
  const client = await auth.getIdTokenClient(audience);
  const headers = await client.getRequestHeaders();
  return headers.Authorization.split(' ')[1];
}

export async function POST(request: Request) {
  try {
    // Get the endpoint at runtime
    const endpoint = getEndpoint();
    
    // Check if endpoint is configured
    if (!endpoint) {
      console.error('LANGGRAPH_ENDPOINT is not set');
      return NextResponse.json({ 
        error: 'Animation service not configured properly. Please contact the administrator.' 
      }, { status: 500 });
    }
    
    const { prompt } = await request.json() as AnimationRequest;
    
    if (!prompt) {
      return NextResponse.json({ error: 'No prompt provided' }, { status: 400 });
    }

    // Log for debugging
    console.log(`Sending request to LangGraph service at: ${endpoint}`);

    // Get ID token for Cloud Run
    const idToken = await getIdToken(endpoint);
    
    // Request to LangGraph Cloud Run service
    const langGraphResponse = await fetchWithRetry(
      `${endpoint}/generate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      },
      {
        maxAttempts: 5,
        initialDelay: 2000,
        maxDelay: 10000,
      }
    );

    const data = await langGraphResponse.json() as AnimationResponse;
    
    if (data.error) {
      return NextResponse.json({ error: data.error }, { status: 500 });
    }
    
    if (data.generation_status !== 'completed') {
      return NextResponse.json({ error: 'Animation generation failed' }, { status: 500 });
    }
    
    if (!data.signed_url) {
      return NextResponse.json({ error: 'No signed URL in response' }, { status: 400 });
    }

    // Fetch the GLB file directly
    const glbResponse = await fetchWithRetry(
      data.signed_url,
      { method: 'GET' },
      {
        maxAttempts: 3,
        initialDelay: 1000,
        maxDelay: 5000,
      }
    );

    // Stream the GLB file to the client
    const headers = new Headers();
    headers.set('Content-Type', 'model/gltf-binary');
    headers.set('Content-Disposition', `inline; filename=${new URL(data.signed_url).pathname.split('/').pop()?.split('?')[0] || 'animation.glb'}`);
    headers.set('Cache-Control', 'no-cache');
    
    return new NextResponse(glbResponse.body, {
      headers
    });
  } catch (error) {
    console.error('Error in animation generation:', error);
    if (error instanceof Response) {
      const errorText = await error.text();
      return NextResponse.json(
        { error: `Backend error: ${errorText}` },
        { status: error.status }
      );
    }
    if (error instanceof Error) {
      return NextResponse.json({ error: `Error: ${error.message}` }, { status: 500 });
    }
    return NextResponse.json({ error: 'An unknown error occurred' }, { status: 500 });
  }
}