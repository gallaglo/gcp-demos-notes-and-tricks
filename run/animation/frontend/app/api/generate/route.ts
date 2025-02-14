import { NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import { fetchWithRetry } from '@/lib/utils';

const BACKEND_SERVICE_URL = process.env.BACKEND_SERVICE_URL || 'https://animator-342279517497.us-central1.run.app';

interface GenerateResponse {
  signed_url: string;
}

async function getIdToken() {
  const auth = new GoogleAuth();
  const client = await auth.getIdTokenClient(BACKEND_SERVICE_URL);
  const headers = await client.getRequestHeaders();
  return headers.Authorization.split(' ')[1];
}

export async function POST(request: Request) {
  try {
    const { prompt } = await request.json();
    if (!prompt) {
      return NextResponse.json({ error: 'No prompt provided' }, { status: 400 });
    }

    const idToken = await getIdToken();
    
    // First request to get signed URL with retry
    const response = await fetchWithRetry(
      `${BACKEND_SERVICE_URL}/generate`,
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

    const data = await response.json() as GenerateResponse;
    const signedUrl = data.signed_url;
    
    if (!signedUrl) {
      return NextResponse.json({ error: 'No signed URL in response' }, { status: 400 });
    }

    // Second request to fetch GLB file with retry
    const glbResponse = await fetchWithRetry(
      signedUrl,
      {
        headers: {
          'Authorization': `Bearer ${idToken}`,
        },
      },
      {
        maxAttempts: 3,
        initialDelay: 1000,
        maxDelay: 5000,
      }
    );

    // Stream the GLB file
    const headers = new Headers();
    headers.set('Content-Type', 'model/gltf-binary');
    headers.set('Content-Disposition', `inline; filename=${new URL(signedUrl).pathname.split('/').pop()?.split('?')[0]}`);
    headers.set('Cache-Control', 'no-cache');
    
    return new NextResponse(glbResponse.body, {
      headers,
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