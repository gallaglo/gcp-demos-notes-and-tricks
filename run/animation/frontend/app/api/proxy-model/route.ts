// app/api/proxy-model/route.ts
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    // Get the signed URL from the request body
    const { url } = await request.json();
    
    if (!url) {
      return NextResponse.json(
        { error: 'URL is required' },
        { status: 400 }
      );
    }

    console.log('Proxying request to:', url);
    
    // Fetch the model from the signed URL on the server side
    // This avoids CORS issues because the request is made server-to-server
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/octet-stream',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch from URL: ${response.statusText}`);
    }

    // Get the data as an ArrayBuffer
    const arrayBuffer = await response.arrayBuffer();
    
    console.log(`Successfully fetched ${arrayBuffer.byteLength} bytes of model data`);
    
    // Return the model data with appropriate headers
    return new Response(arrayBuffer, {
      headers: {
        'Content-Type': 'application/octet-stream',
        'Cache-Control': 'no-cache',
      },
    });
  } catch (error) {
    console.error('Error in proxy-model API route:', error);
    
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}