'use client';

import { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Sparkles, Layers } from "lucide-react";
import ChatInterface from "@/components/ChatInterface";
import { useAnimationStream } from '@/lib/hooks/useAnimationStream';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SceneEditValue } from '@/lib/types/scene';

// Define example prompts
const EXAMPLE_PROMPTS = [
  "planets orbiting sun in solar system",
  "tumbling cube",
  "bouncing ball"
];

// Dynamically import Three.js components with ssr: false to prevent window errors
const ThreeJSViewer = dynamic(() => import('@/components/ThreeJSViewer'), { ssr: false });
const SceneControls = dynamic(() => import('@/components/SceneControls'), { ssr: false });

export default function Home() {
  const [isMounted, setIsMounted] = useState(false);
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("preview");
  const [viewerStatus, setViewerStatus] = useState<string>("");
  
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
    sceneState,
    sceneHistory,
    fetchSceneHistory
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

  // Handle status changes from viewer component
  const handleStatusChange = (newStatus: string) => {
    setViewerStatus(newStatus);
    console.log("Animation status:", newStatus);
  };
  
  // Handle errors from viewer component
  const handleError = (error: string) => {
    console.error("Animation viewer error:", error);
  };

  // Handle example prompt selection
  const handleExampleSelect = (prompt: string) => {
    generateAnimation(prompt);
  };

  // REMOVE the local SceneEditValue type definition
  // It's already imported from '@/lib/types/scene'

  // Handle scene edit request
  const handleSceneEdit = useCallback((objectId: string, changeType: string, value: SceneEditValue) => {
    // This would be implemented to make direct edits to the scene
    console.log('Scene edit:', objectId, changeType, value);
    // In a real implementation, this would update the scene
  }, []);

  // Generate a new prompt based on scene controls
  const handleGeneratePrompt = useCallback((prompt: string) => {
    generateAnimation(prompt);
  }, [generateAnimation]);

  // Fetch scene history if we have a scene
  useEffect(() => {
    if (sceneState && fetchSceneHistory) {
      fetchSceneHistory();
    }
  }, [sceneState, fetchSceneHistory]);

  return (
    <div className="flex flex-col h-screen max-h-screen overflow-hidden">
      {/* Header - fixed height */}
      <div className="container flex-shrink-0 flex flex-col gap-4 p-4 lg:p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Animation Generator</h1>
          <div className="flex gap-2">
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
                    onClick={() => handleExampleSelect(examplePrompt)}
                  >
                    {examplePrompt}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            
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
      
      {/* Main content area - takes remaining height */}
      <div 
        className="container flex-1 min-h-0 grid gap-6 p-4 lg:p-8 md:grid-cols-[1fr_1fr]"
        style={{ height: 'calc(100vh - 124px)' }}
      >
        
        {/* Chat Interface */}
        <div className="flex flex-col h-full min-h-0 max-h-full">
          <Card className="flex-1 overflow-hidden min-h-0 flex flex-col">
            <CardContent className="p-4 overflow-hidden flex-1 flex flex-col min-h-0">
              <ChatInterface
                messages={messages}
                isLoading={isLoading}
                onSendMessageAction={handleSendMessage}
                onStopAction={stopGeneration}
              />
            </CardContent>
          </Card>
        </div>

        {/* Animation Viewer and Scene Controls Panel */}
        <div className="flex flex-col h-full min-h-0">
          <Tabs 
            defaultValue="preview" 
            className="flex-1 flex flex-col min-h-0"
            value={activeTab}
            onValueChange={setActiveTab}
          >
            <div className="flex justify-between items-center mb-2">
              <TabsList>
                <TabsTrigger value="preview">Preview</TabsTrigger>
                <TabsTrigger value="scene" disabled={!sceneState}>
                  <Layers className="mr-2 h-4 w-4" />
                  Scene Editor
                </TabsTrigger>
              </TabsList>
            </div>
            
            <TabsContent value="preview" className="flex-1 min-h-0 flex flex-col">
              <Card className="flex-1 overflow-hidden min-h-0">
                <CardContent className="p-0 h-full min-h-0">
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
            </TabsContent>
            
            <TabsContent value="scene" className="flex-1 min-h-0 flex flex-col">
              <Card className="flex-1 overflow-hidden min-h-0">
                <CardContent className="p-4 h-full min-h-0 overflow-y-auto">
                  {isMounted && sceneState ? (
                    <SceneControls
                      sceneState={sceneState}
                      sceneHistory={sceneHistory}
                      onObjectEdit={handleSceneEdit}
                      onGeneratePrompt={handleGeneratePrompt}
                      onUndo={() => console.log('Undo requested')}
                    />
                  ) : (
                    <div className="h-full flex items-center justify-center">
                      <p className="text-muted-foreground">
                        Generate an animation to edit the scene
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
          
          {/* Status and Error Messages */}
          <div className="mt-4 space-y-2 flex-shrink-0">
            {status && (
              <Alert>
                <AlertDescription className="flex justify-between">
                  <span>{status}</span>
                  {viewerStatus && <span className="text-xs text-muted-foreground">{viewerStatus}</span>}
                </AlertDescription>
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
    </div>
  );
}