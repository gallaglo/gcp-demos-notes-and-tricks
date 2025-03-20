'use client';

import { useState, useCallback } from 'react';
import { useStream } from "@langchain/langgraph-sdk/react";
import { v4 as uuidv4 } from 'uuid';

export type MessageType = {
  id: string;
  type: 'human' | 'ai';
  content: string;
};

export type AnimationState = {
  messages: MessageType[];
  signedUrl?: string;
  status?: string;
};

// Define custom event types
type AnimationCustomEvent = {
  type: 'data' | 'status' | 'error';
  data?: {
    signed_url?: string;
    status?: string;
  };
  error?: string;
};

export function useAnimationStream() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [signedUrl, setSignedUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  const [isError, setIsError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  
  // Check if we're in a browser environment
  const isClient = typeof window !== 'undefined';
  
  // Get the API base URL
  const getApiBaseUrl = () => {
    if (isClient) {
      // Use the same origin for API requests from the browser
      return `${window.location.origin}/api`;
    }
    // This will only be used server-side
    return process.env.NEXT_PUBLIC_API_BASE_URL || '/api';
  };
  
  // Initialize the useStream hook
  const thread = useStream<AnimationState>({
    apiUrl: getApiBaseUrl(),
    assistantId: "animation-generator",
    messagesKey: "messages",
    threadId: threadId,
    onThreadId: setThreadId,
    // Handle custom events
    onCustomEvent: (event: unknown) => {
      const customEvent = event as AnimationCustomEvent;
      
      if (customEvent.type === 'data' && customEvent.data?.signed_url) {
        setSignedUrl(customEvent.data.signed_url);
      }
      
      if (customEvent.type === 'status' && customEvent.data?.status) {
        setStatus(customEvent.data.status);
      }
      
      if (customEvent.type === 'error') {
        setIsError(true);
        setErrorMessage(customEvent.error || 'An unknown error occurred');
        setStatus('Error');
      }
    }
  });
  
  // Generate animation with streaming updates
  const generateAnimation = useCallback((prompt: string) => {
    // Reset state for new generation
    setSignedUrl(null);
    setIsError(false);
    setErrorMessage('');
    setStatus('Starting generation');
    
    // Submit the message to the thread
    thread.submit({
      messages: [{ 
        id: uuidv4(),
        type: "human", 
        content: prompt 
      }],
    });
  }, [thread]);
  
  return {
    generateAnimation,
    isLoading: thread.isLoading,
    stopGeneration: thread.stop,
    messages: thread.messages,
    signedUrl,
    status,
    isError,
    errorMessage,
  };
}