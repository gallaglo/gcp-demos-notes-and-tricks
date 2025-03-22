'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ArrowUpDown } from "lucide-react";
import ChatInterface from "@/components/ChatInterface";
import { useAnimationStream } from '@/lib/hooks/useAnimationStream';

// Dynamically import Three.js components with ssr: false to prevent window errors
const ThreeJSViewer = dynamic(() => import('@/components/ThreeJSViewer'), { ssr: false });

export default function Home() {
  const [isMounted, setIsMounted] = useState(false);
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(true);
  const [layoutMode, setLayoutMode] = useState<'side-by-side' | 'stacked'>('side-by-side');
  
  // Use the animation stream hook
  const {
    generateAnimation,
    isLoading,
    stopGeneration,
    clearConversation,
    messages,
    signedUrl,
    status,
    isError,
    errorMessage,
  } = useAnimationStream();

  // Set isMounted to true after component mounts
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  // Handle sending a new message
  const handleSendMessage = async (message: string) => {
    generateAnimation(message);
  };

  // Toggle layout between side-by-side and stacked
  const toggleLayout = () => {
    setLayoutMode(prev => prev === 'side-by-side' ? 'stacked' : 'side-by-side');
  };

  // Handle status changes from viewer component
  const handleStatusChange = () => {
    // Status is already handled by useAnimationStream
  };
  
  // Handle errors from viewer component
  const handleError = () => {
    // Errors are already handled by useAnimationStream
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="container flex flex-col gap-4 p-4 lg:p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Animation Generator</h1>
          <div className="flex gap-2">
            <Button 
              onClick={toggleLayout} 
              variant="outline" 
              size="sm"
            >
              <ArrowUpDown className="mr-2 h-4 w-4" />
              Toggle Layout
            </Button>
            <Button 
              onClick={() => clearConversation()} 
              variant="outline" 
              size="sm"
              className="text-red-500 hover:bg-red-50"
            >
              Clear Chat
            </Button>
          </div>
        </div>
        <Separator />
      </div>
      
      <div className={`container grid flex-1 gap-6 lg:p-8 
        ${layoutMode === 'side-by-side' ? 'md:grid-cols-[1fr_1fr]' : 'grid-cols-1'}`}>
        
        {/* Chat Interface */}
        <div className="flex flex-col gap-4 h-full">
          <ChatInterface
            messages={messages}
            isLoading={isLoading}
            onSendMessageAction={handleSendMessage}
            onStopAction={stopGeneration}
          />
        </div>

        {/* Animation Viewer Panel */}
        <div className="flex flex-col gap-4 h-full">
          <Card className="flex-1">
            <CardContent className="p-0 h-full">
              {/* Only render the ThreeJSViewer component when mounted (client-side) */}
              {isMounted && (
                <ThreeJSViewer 
                  signedUrl={signedUrl} 
                  initialIsPlaying={isAnimationPlaying}
                  onPlayingChange={setIsAnimationPlaying}
                  onStatusChange={handleStatusChange}
                  onError={handleError}
                />
              )}
            </CardContent>
          </Card>
          
          {status && (
            <Alert>
              <AlertDescription>{status}</AlertDescription>
            </Alert>
          )}

          {isError && (
            <Alert variant="destructive">
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </div>
  );
}