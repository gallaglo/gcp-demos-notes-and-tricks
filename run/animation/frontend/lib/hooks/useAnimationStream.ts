'use client';

import { useState, useCallback, useEffect } from 'react';
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
  type: 'data' | 'status' | 'error' | 'message' | 'state' | 'end';
  data?: {
    signed_url?: string;
    status?: string;
    content?: string;
    id?: string;
    type?: string;
    messages?: MessageType[];
  };
  error?: string;
};

export function useAnimationStream() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [signedUrl, setSignedUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Effect to load thread from localStorage on first mount
  useEffect(() => {
    const savedThreadId = localStorage.getItem('animationThreadId');
    if (savedThreadId) {
      setThreadId(savedThreadId);
      
      // Fetch the thread data
      fetchThreadData(savedThreadId).catch(console.error);
    }
  }, []);
  
  // Function to fetch thread data
  const fetchThreadData = async (threadId: string) => {
    try {
      const response = await fetch(`${getBaseUrl()}/api/thread/${threadId}`);
      
      if (!response.ok) {
        // If thread not found, clear local storage
        if (response.status === 404) {
          localStorage.removeItem('animationThreadId');
          setThreadId(null);
        }
        return;
      }
      
      const data = await response.json();
      
      // Update state
      if (data.messages) {
        setMessages(data.messages);
      }
      
      if (data.signedUrl) {
        setSignedUrl(data.signedUrl);
      }
      
      if (data.status) {
        setStatus(data.status);
      }
    } catch (error) {
      console.error("Error fetching thread data:", error);
    }
  };

  // Get the base URL dynamically in the browser
  const getBaseUrl = () => {
    if (typeof window !== 'undefined') {
      return `${window.location.protocol}//${window.location.host}`;
    }
    return '';
  };
  
  // Process events from the stream
  const handleEvent = useCallback((event: AnimationCustomEvent) => {
    console.log("Received event:", event);
    
    switch (event.type) {
      case 'state':
        if (event.data && event.data.messages && Array.isArray(event.data.messages)) {
          setMessages(event.data.messages);
        }
        break;
        
      case 'message':
        if (event.data) {
          const messageData = {
            id: event.data.id || uuidv4(),
            type: event.data.type as 'human' | 'ai' || 'ai',
            content: event.data.content || '',
          };
          
          // Check if we already have this message (by id)
          setMessages(prev => {
            const exists = prev.some(msg => msg.id === messageData.id);
            if (exists) {
              return prev;
            }
            return [...prev, messageData];
          });
        }
        break;
        
      case 'data':
        if (event.data?.signed_url) {
          setSignedUrl(event.data.signed_url);
        }
        break;
        
      case 'status':
        if (event.data?.status) {
          setStatus(event.data.status);
        }
        break;
        
      case 'error':
        setIsError(true);
        setErrorMessage(event.error || 'An unknown error occurred');
        setStatus('Error');
        break;
        
      case 'end':
        setIsLoading(false);
        break;
    }
  }, []);
  
  // Function to create a thread and stream events
  const generateAnimation = useCallback(async (prompt: string) => {
    // Don't reset messages anymore, we want to keep the conversation history
    setIsError(false);
    setErrorMessage('');
    setStatus('Processing your request...');
    setIsLoading(true);
    
    try {
      // Create a new message object
      const newMessage: MessageType = { 
        id: uuidv4(),
        type: "human", 
        content: prompt 
      };
      
      // Create a new thread or use existing one
      const endpoint = threadId 
        ? `${getBaseUrl()}/api/thread/${threadId}` 
        : `${getBaseUrl()}/api/thread/new`;
      
      console.log(`Sending request to: ${endpoint}`);
      
      // Send request to create/update thread
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [newMessage],
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status} ${errorText}`);
      }
      
      // If this is a new thread, save the thread ID from the URL
      if (!threadId && response.url) {
        const urlParts = response.url.split('/');
        const newThreadId = urlParts[urlParts.length - 1];
        if (newThreadId && newThreadId !== 'new') {
          setThreadId(newThreadId);
          // Save to localStorage for persistence across refreshes
          localStorage.setItem('animationThreadId', newThreadId);
        }
      }
      
      // Handle streaming response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Failed to get response reader");
      }
      
      const decoder = new TextDecoder();
      let buffer = "";
      
      // Process the stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.trim() === '' || !line.startsWith('data: ')) continue;
          
          try {
            const eventData = JSON.parse(line.substring(6)) as AnimationCustomEvent;
            handleEvent(eventData);
          } catch (e) {
            console.error("Failed to parse event:", line, e);
          }
        }
      }
      
      // Process any remaining data
      if (buffer.trim() !== '') {
        const lines = buffer.split("\n\n");
        for (const line of lines) {
          if (line.trim() === '' || !line.startsWith('data: ')) continue;
          
          try {
            const eventData = JSON.parse(line.substring(6)) as AnimationCustomEvent;
            handleEvent(eventData);
          } catch (e) {
            console.error("Failed to parse event:", line, e);
          }
        }
      }
      
      setIsLoading(false);
    } catch (error) {
      console.error("Animation stream error:", error);
      setIsError(true);
      setErrorMessage(error instanceof Error ? error.message : 'Unknown error');
      setStatus('Error');
      setIsLoading(false);
    }
  }, [threadId, handleEvent]);
  
  // Function to stop the generation
  const stopGeneration = useCallback(() => {
    setIsLoading(false);
  }, []);
  
  // Function to clear chat history and start a new conversation
  const clearConversation = useCallback(() => {
    setMessages([]);
    setSignedUrl(null);
    setStatus('');
    setIsError(false);
    setErrorMessage('');
    setThreadId(null);
    localStorage.removeItem('animationThreadId');
  }, []);
  
  return {
    generateAnimation,
    isLoading,
    stopGeneration,
    clearConversation,
    messages,
    signedUrl,
    status,
    isError,
    errorMessage,
  };
}