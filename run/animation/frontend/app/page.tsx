'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Sparkles, Loader2 } from "lucide-react";
import { useAnimationStream } from '@/lib/hooks/useAnimationStream';
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

  // Use our animation stream hook
  const {
    generateAnimation,
    isLoading,
    messages,
    signedUrl,
    status,
    isError,
    errorMessage
  } = useAnimationStream();

  // Set isMounted to true after component mounts
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    
    // Use our streaming hook to generate the animation
    generateAnimation(prompt);
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

            {isError && (
              <Alert variant="destructive">
                <AlertDescription>{errorMessage}</AlertDescription>
              </Alert>
            )}

            {/* Messages Panel - Show streaming updates */}
            {messages.length > 1 && (
              <Card className="max-h-[220px] overflow-y-auto">
                <CardContent className="pt-4">
                  <h3 className="font-semibold mb-2">Generation Log</h3>
                  <div className="space-y-2">
                    {messages.map((message) => (
                      <div key={message.id} className="text-sm">
                        {typeof message.content === 'string' 
                          ? message.content 
                          : JSON.stringify(message.content)}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
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
                />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}