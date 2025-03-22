'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Sparkles, Loader2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Dynamically import Three.js components with ssr: false to prevent window errors
const ThreeJSViewer = dynamic(() => import('@/components/ThreeJSViewer'), { ssr: false });

const EXAMPLE_PROMPTS = [
  "planets orbiting sun in solar system",
  "tumbling cube",
  "bouncing ball"
];

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(true);
  const [isMounted, setIsMounted] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [signedUrl, setSignedUrl] = useState<string | null>(null);

  // Set isMounted to true after component mounts
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    
    setIsLoading(true);
    setSignedUrl(null);
    setStatus('Generating animation...');
    setError('');
    
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      if (!data.signed_url) {
        throw new Error('No URL received from server');
      }
      
      // Set the signed URL for the ThreeJSViewer component
      setSignedUrl(data.signed_url);
      setStatus('Animation generated. Loading 3D model...');
      
    } catch (error) {
      console.error('Error generating animation:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle status changes from viewer component
  const handleStatusChange = (newStatus: string) => {
    setStatus(newStatus);
  };
  
  // Handle errors from viewer component
  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="container flex flex-col gap-4 p-4 lg:p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Animation Generator</h1>
        </div>
        <Separator />
      </div>
      
      <div className="container grid flex-1 gap-6 md:grid-cols-[380px_1fr] lg:p-8">
        {/* Left Panel - Controls */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-4">
            <Card>
              <CardContent className="pt-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm text-muted-foreground">
                        Enter prompt or select an example
                      </label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" size="sm">
                            <Sparkles className="mr-2 h-4 w-4" />
                            Examples
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {EXAMPLE_PROMPTS.map((examplePrompt) => (
                            <DropdownMenuItem
                              key={examplePrompt}
                              onClick={() => setPrompt(examplePrompt)}
                            >
                              {examplePrompt}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    <Textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Describe your animation..."
                      className="min-h-[150px]"
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      'Generate Animation'
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {status && (
              <Alert>
                <AlertDescription>{status}</AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
        </div>

        {/* Right Panel - Preview */}
        <div className="flex flex-col gap-4">
          <Card className="flex-1">
            <CardContent className="p-0">
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
        </div>
      </div>
    </div>
  );
}