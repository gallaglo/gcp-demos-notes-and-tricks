// app/page.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sparkles, Send, Loader2 } from "lucide-react";
import { useMCPClient } from '@/lib/hooks/useMCPClient';

// Dynamically import ThreeJS components with SSR disabled
const ThreeJSViewer = dynamic(() => import('@/components/ThreeJSViewer'), { ssr: false });

// Example prompts
const EXAMPLE_PROMPTS = [
  "Create a red ball bouncing on a blue floor",
  "Generate a rotating cube with colorful sides",
  "Make planets orbiting around a bright sun"
];

export default function AnimationChatPage() {
  // State management
  const [input, setInput] = useState('');
  const [isMounted, setIsMounted] = useState(false);
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(true);
  const [status, setStatus] = useState('');
  
  // Use our MCP client hook
  const { 
    messages, 
    isLoading, 
    animationData, 
    error, 
    sendMessage, 
    clearChat 
  } = useMCPClient();
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Set isMounted after component mounts (for ThreeJS)
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Focus input on initial load
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // Update status when animation data changes
  useEffect(() => {
    if (animationData) {
      setStatus(`Animation ready! Valid for ${animationData.expiration || '15 minutes'}`);
    }
  }, [animationData]);

  // Handle keydown in the textarea
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        sendMessage(input);
        setInput('');
      }
    }
  };

  // Handle status changes from viewer component
  const handleStatusChange = (newStatus: string) => {
    setStatus(prevStatus => `${prevStatus} - Viewer: ${newStatus}`);
  };
  
  // Handle errors from viewer component
  const handleError = (errorMessage: string) => {
    setStatus(`Viewer error: ${errorMessage}`);
  };

  // Handle example prompt selection
  const handleExampleSelect = (prompt: string) => {
    setInput(prompt);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="container mx-auto p-4 min-h-screen flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 flex flex-col gap-4 mb-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">3D Animation Generator</h1>
          <div className="flex gap-2">
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_PROMPTS.map((prompt, index) => (
                <Button 
                  key={index} 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleExampleSelect(prompt)}
                  className="text-xs"
                >
                  <Sparkles className="mr-1 h-3 w-3" />
                  {prompt.length > 20 ? prompt.substring(0, 17) + '...' : prompt}
                </Button>
              ))}
            </div>
            
            <Button 
              onClick={clearChat} 
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
      
      {/* Main content area - takes remaining height */}
      <div 
        className="flex-1 min-h-0 grid gap-6 md:grid-cols-[1fr_1fr]"
        style={{ height: 'calc(100vh - 124px)' }}
      >
        {/* Chat Interface */}
        <div className="flex flex-col h-full min-h-0 max-h-full">
          <Card className="flex-1 overflow-hidden min-h-0 flex flex-col">
            <CardContent className="p-4 overflow-hidden flex-1 flex flex-col min-h-0">
              {/* Message Display Area */}
              <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2">
                <div className="flex flex-col gap-4 pb-2">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className="flex items-start gap-3 max-w-[80%]">
                        {message.role === 'assistant' && (
                          <Avatar className="mt-1 flex-shrink-0">
                            <AvatarFallback className="bg-primary text-primary-foreground">AI</AvatarFallback>
                          </Avatar>
                        )}
                        
                        <div
                          className={`py-2 px-3 rounded-lg ${
                            message.role === 'user'
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted'
                          }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        </div>
                        
                        {message.role === 'user' && (
                          <Avatar className="mt-1 flex-shrink-0">
                            <AvatarFallback className="bg-secondary">You</AvatarFallback>
                          </Avatar>
                        )}
                      </div>
                    </div>
                  ))}
                  
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="flex items-start gap-3">
                        <Avatar className="mt-1 flex-shrink-0">
                          <AvatarFallback className="bg-primary text-primary-foreground">AI</AvatarFallback>
                        </Avatar>
                        <div className="py-3 px-3 rounded-lg bg-muted flex items-center">
                          <div className="flex gap-1">
                            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" style={{ animationDelay: "0ms" }}></div>
                            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" style={{ animationDelay: "300ms" }}></div>
                            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" style={{ animationDelay: "600ms" }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div ref={messagesEndRef} />
                </div>
              </div>
              
              {/* Input Area */}
              <div className="flex items-end gap-2 pt-4">
                <Textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Describe the animation you want to create..."
                  className="min-h-[60px] flex-1 resize-none"
                  disabled={isLoading}
                />
                <Button
                  variant="default"
                  size="icon"
                  onClick={() => {
                    if (input.trim() && !isLoading) {
                      sendMessage(input);
                      setInput('');
                    }
                  }}
                  disabled={isLoading || !input.trim()}
                  className="h-[60px] w-[60px]"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Animation Viewer Panel */}
        <div className="flex flex-col h-full min-h-0">
          <Card className="flex-1 overflow-hidden min-h-0">
            <CardContent className="p-0 h-full min-h-0">
              {/* Only render the ThreeJSViewer component when mounted (client-side) */}
              {isMounted && (
                <ThreeJSViewer 
                  signedUrl={animationData?.signed_url || null} 
                  initialIsPlaying={isAnimationPlaying}
                  onPlayingChange={setIsAnimationPlaying}
                  onStatusChange={handleStatusChange}
                  onError={handleError}
                />
              )}
            </CardContent>
          </Card>
          
          {status && (
            <Alert className="mt-4 flex-shrink-0">
              <AlertDescription>{status}</AlertDescription>
            </Alert>
          )}

          {error && (
            <Alert variant="destructive" className="mt-4 flex-shrink-0">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </div>
  );
}