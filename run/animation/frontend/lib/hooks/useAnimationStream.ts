'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
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
  
  // Use a ref to track the current prompt being processed to avoid duplicates
  const currentPromptRef = useRef<string | null>(null);
  
  // Use a Set to track messages we've already added locally
  const localMessageContentsRef = useRef<Set<string>>(new Set());

  // Get the base URL dynamically in the browser
  const getBaseUrl = useCallback(() => {
    if (typeof window !== 'undefined') {
      return `${window.location.protocol}//${window.location.host}`;
    }
    return '';
  }, []);
  
  // Function to fetch thread data
  const fetchThreadData = useCallback(async (threadId: string) => {
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
        
        // Update our local message tracking set
        data.messages.forEach((msg: MessageType) => {
          localMessageContentsRef.current.add(msg.content);
        });
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
  }, [getBaseUrl]);
  
  // Effect to load thread from localStorage on first mount
  useEffect(() => {
    const savedThreadId = localStorage.getItem('animationThreadId');
    if (savedThreadId) {
      setThreadId(savedThreadId);
      
      // Fetch the thread data
      fetchThreadData(savedThreadId).catch(console.error);
    }
  }, [fetchThreadData]);
  
  // Process events from the stream
  const handleEvent = useCallback((event: AnimationCustomEvent) => {
    console.log("Received event:", event);
    
    switch (event.type) {
      case 'state': {
        // Use a block scope to avoid variable name conflicts
        const data = event.data;
        if (!data) break;
        
        const serverMessages = data.messages;
        if (!serverMessages || !Array.isArray(serverMessages)) break;
        
        // Don't completely replace messages; merge with existing ones
        setMessages(prevMessages => {
          // Create a map of existing messages by ID for quick lookup
          const existingMessagesMap = new Map(
            prevMessages.map(msg => [msg.id, msg])
          );
          
          // Add any new messages from the server that we don't have yet
          for (const serverMsg of serverMessages) {
            if (!existingMessagesMap.has(serverMsg.id)) {
              existingMessagesMap.set(serverMsg.id, serverMsg);
            }
          }
          
          // Convert back to array and sort by insertion order
          // This preserves the conversation flow
          return Array.from(existingMessagesMap.values());
        });
        break;
      }
        
      case 'message': {
        const data = event.data;
        if (!data) break;
        
        const id = data.id || uuidv4();
        let messageType: 'human' | 'ai' = 'ai';
        
        if (data.type === 'human' || data.type === 'ai') {
          messageType = data.type;
        }
        
        const messageContent = data.content || '';
        
        // Skip initial messages that match our current prompt's initial message
        if (messageType === 'ai' && 
            currentPromptRef.current && 
            messageContent.includes(`I'm generating a 3D animation based on your request: '${currentPromptRef.current}'`)) {
          console.log("Skipping duplicate initial message:", messageContent);
          return;
        }
        
        // Check if we've already seen this message content
        if (localMessageContentsRef.current.has(messageContent)) {
          console.log("Skipping already displayed message:", messageContent);
          return;
        }
        
        const messageData: MessageType = {
          id,
          type: messageType,
          content: messageContent
        };
        
        // Add to our local tracking set
        localMessageContentsRef.current.add(messageContent);
        
        // Add the message to the UI
        setMessages(prev => {
          // Check if we already have this message (by id)
          const exists = prev.some(msg => msg.id === messageData.id);
          if (exists) {
            return prev;
          }
          return [...prev, messageData];
        });
        break;
      }
        
      case 'data': {
        const data = event.data;
        if (!data) break;
        
        const url = data.signed_url;
        if (url) {
          setSignedUrl(url);
        }
        break;
      }
        
      case 'status': {
        const data = event.data;
        if (!data) break;
        
        const newStatus = data.status;
        if (newStatus) {
          setStatus(newStatus);
        }
        break;
      }
        
      case 'error': {
        setIsError(true);
        setErrorMessage(event.error || 'An unknown error occurred');
        setStatus('Error');
        break;
      }
        
      case 'end': {
        setIsLoading(false);
        currentPromptRef.current = null; // Clear current prompt when done
        break;
      }
    }
  }, []);
  
  // Function to create a thread and stream events
  const generateAnimation = useCallback(async (prompt: string) => {
    setIsError(false);
    setErrorMessage('');
    setStatus('Processing your request...');
    setIsLoading(true);
    
    // Store the current prompt to help with deduplication
    currentPromptRef.current = prompt;
    
    try {
      // Create a new message object for the human's prompt
      const humanMessage: MessageType = { 
        id: uuidv4(),
        type: "human", 
        content: prompt 
      };
      
      // Add the initial processing message 
      const initialMessage: MessageType = {
        id: uuidv4(),
        type: "ai",
        content: `I'm generating a 3D animation based on your request: '${prompt}'. This might take a moment...`
      };
      
      // Track these messages locally
      localMessageContentsRef.current.add(humanMessage.content);
      localMessageContentsRef.current.add(initialMessage.content);
      
      // Add the human message and initial AI message immediately
      setMessages(prevMessages => [...prevMessages, humanMessage, initialMessage]);
      
      // Create a new thread or use existing one
      const endpoint = threadId 
        ? `${getBaseUrl()}/api/thread/${threadId}` 
        : `${getBaseUrl()}/api/thread/new`;
      
      console.log(`Sending request to: ${endpoint}`);
      
      // Send request to create/update thread (only send the human message)
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [humanMessage],
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
      currentPromptRef.current = null;
    } catch (error) {
      console.error("Animation stream error:", error);
      setIsError(true);
      setErrorMessage(error instanceof Error ? error.message : 'Unknown error');
      setStatus('Error');
      setIsLoading(false);
      currentPromptRef.current = null;
      
      // Add an error message
      const errorContent = "Sorry, there was an error generating the animation. You can try another prompt if you'd like.";
      
      // Only add if we haven't already
      if (!localMessageContentsRef.current.has(errorContent)) {
        localMessageContentsRef.current.add(errorContent);
        
        setMessages(prev => [
          ...prev, 
          {
            id: uuidv4(),
            type: 'ai',
            content: errorContent
          }
        ]);
      }
    }
  }, [threadId, handleEvent, getBaseUrl]);
  
  // Function to stop the generation
  const stopGeneration = useCallback(() => {
    setIsLoading(false);
    currentPromptRef.current = null;
    
    // Add a message indicating the generation was stopped
    const stoppedContent = "The animation generation was interrupted. You can try another prompt if you'd like.";
    
    // Only add if we haven't already
    if (!localMessageContentsRef.current.has(stoppedContent)) {
      localMessageContentsRef.current.add(stoppedContent);
      
      setMessages(prev => [
        ...prev,
        {
          id: uuidv4(),
          type: 'ai',
          content: stoppedContent
        }
      ]);
    }
  }, []);
  
  // Function to clear chat history and start a new conversation
  const clearConversation = useCallback(() => {
    setMessages([]);
    setSignedUrl(null);
    setStatus('');
    setIsError(false);
    setErrorMessage('');
    setThreadId(null);
    currentPromptRef.current = null;
    localMessageContentsRef.current.clear();
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