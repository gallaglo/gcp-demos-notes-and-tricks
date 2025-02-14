import { NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';

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
    
    const response = await fetch(`${BACKEND_SERVICE_URL}/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json({ error: `Backend error: ${error}` }, { status: response.status });
    }

    const data = await response.json() as GenerateResponse;
    const signedUrl = data.signed_url;

    if (!signedUrl) {
      return NextResponse.json({ error: 'No signed URL in response' }, { status: 400 });
    }

    // Fetch GLB file
    const glbResponse = await fetch(signedUrl, {
      headers: {
        'Authorization': `Bearer ${idToken}`,
      },
    });

    if (!glbResponse.ok) {
      const errorText = await glbResponse.text();
      return NextResponse.json(
        { error: `Failed to fetch GLB file: ${errorText}` },
        { status: glbResponse.status }
      );
    }

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
    if (error instanceof Error) {
      return NextResponse.json({ error: `Error: ${error.message}` }, { status: 500 });
    }
    return NextResponse.json({ error: 'An unknown error occurred' }, { status: 500 });
  }
}