'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import the ThreeJSViewer with correct type handling
const DynamicThreeJSViewer = dynamic(
  () => import('@/components/ThreeJSViewer'),
  { ssr: false }
);

// Define props for our wrapper - must match ThreeJSViewer props
interface ViewerWrapperProps {
  signedUrl: string | null;
  initialIsPlaying?: boolean;
  onPlayingChange?: (playing: boolean) => void;
  onError?: (error: string) => void;
  onStatusChange?: (status: string) => void;
}

/**
 * Wrapper component that handles the dynamic import of ThreeJSViewer
 * and passes props correctly
 */
export default function ViewerWrapper(props: ViewerWrapperProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  // Server-side rendering placeholder
  if (!isMounted) {
    return <div className="w-full h-[calc(100vh-12rem)] rounded-lg bg-gray-100"></div>;
  }

  // Client-side rendering with the actual viewer
  // Use type assertion to avoid TypeScript errors with dynamic imports
  return <DynamicThreeJSViewer {...props} />;
}