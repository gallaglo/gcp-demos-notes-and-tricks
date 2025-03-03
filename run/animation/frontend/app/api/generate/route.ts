import { NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import { fetchWithRetry } from '@/lib/utils';

// Vertex AI Reasoning Engine endpoint - add type assertion to handle TypeScript error
const VERTEX_ENDPOINT = process.env.VERTEX_ENDPOINT as string;
if (!VERTEX_ENDPOINT) {
  throw new Error("VERTEX_ENDPOINT environment variable is not set");
}

interface VertexRequest {
  prompt: string;
}

interface VertexResponse {
  predictions: Array<{
    generation_status: string;
    signed_url?: string;
    error?: string;
  }>;
}

async function getIdToken(audience: string) {
  const auth = new GoogleAuth();
  const client = await auth.getIdTokenClient(audience);
  const headers = await client.getRequestHeaders();
  return headers.Authorization.split(' ')[1];
}

export async function POST(request: Request) {
  try {
    const { prompt } = await request.json() as VertexRequest;
    
    if (!prompt) {
      return NextResponse.json({ error: 'No prompt provided' }, { status: 400 });
    }

    // Get ID token for Vertex AI
    const idToken = await getIdToken(VERTEX_ENDPOINT);
    
    // Request to Vertex AI Reasoning Engine
    const vertexResponse = await fetchWithRetry(
      VERTEX_ENDPOINT,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          instances: [
            {
              prompt: prompt
            }
          ]
        }),
      },
      {
        maxAttempts: 5,
        initialDelay: 2000,
        maxDelay: 10000,
      }
    );

    const data = await vertexResponse.json() as VertexResponse;
    
    // Extract the result from the Vertex AI response
    const result = data.predictions[0];
    
    if (result.error) {
      return NextResponse.json({ error: result.error }, { status: 500 });
    }
    
    if (result.generation_status !== 'completed') {
      return NextResponse.json({ error: 'Animation generation failed' }, { status: 500 });
    }
    
    if (!result.signed_url) {
      return NextResponse.json({ error: 'No signed URL in response' }, { status: 400 });
    }

    // Fetch the GLB file directly
    const glbResponse = await fetchWithRetry(
      result.signed_url,
      {
        method: 'GET'
      },
      {
        maxAttempts: 3,
        initialDelay: 1000,
        maxDelay: 5000,
      }
    );

    // Stream the GLB file to the client
    const headers = new Headers();
    headers.set('Content-Type', 'model/gltf-binary');
    headers.set('Content-Disposition', `inline; filename=${new URL(result.signed_url).pathname.split('/').pop()?.split('?')[0] || 'animation.glb'}`);
    headers.set('Cache-Control', 'no-cache');
    
    return new NextResponse(glbResponse.body, {
      headers
    });
  } catch (error) {
    console.error('Error:', error);
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