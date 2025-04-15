'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { SceneState } from '@/lib/types/scene';
import { AgentClient, Message as AgentMessage } from '@/lib/agentClient';

export type MessageType = {
  id: string;
  type: 'human' | 'ai';
  content: string;
  metadata?: {
    sceneId?: string;
    modifiedObjects?: string[];
    action?: 'create' | 'modify' | 'delete';
  };
};

export type AnimationState = {
  messages: MessageType[];
  signedUrl?: string;
  status?: string;
  sceneState?: SceneState;
  sceneHistory?: SceneState[];
};

// Define custom event types
type AnimationCustomEvent = {
  type: 'data' | 'status' | 'error' | 'message' | 'state' | 'end' | 'scene_state' | 'scene_history';
  data?: {
    signed_url?: string;
    signedUrl?: string;
    status?: string;
    content?: string;
    id?: string;
    type?: string;
    messages?: MessageType[];
    scene_id?: string;
    scene_state?: SceneState;
    scene_history?: SceneState[];
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
  
  // Scene state management
  const [sceneState, setSceneState] = useState<SceneState | undefined>(undefined);
  const [sceneHistory, setSceneHistory] = useState<SceneState[]>([]);
  
  // Use a ref to track the current prompt being processed to avoid duplicates
  const currentPromptRef = useRef<string | null>(null);
  
  // Use a Set to track message IDs we've already added to prevent duplicates
  const messageIdsRef = useRef<Set<string>>(new Set());
  
  // Use a Set to track human/user message contents to prevent duplicates
  const humanMessageContentsRef = useRef<Set<string>>(new Set());
  
  // Use a Map to track AI message content we've already added to prevent duplicates
  const aiMessageContentsRef = useRef<Map<string, boolean>>(new Map());

  // Store threadId in a ref to make sure we always have the latest value in callbacks
  const threadIdRef = useRef<string | null>(null);

  // Agent client for API communication
  const agentClientRef = useRef<AgentClient | null>(null);

  // Update threadIdRef whenever threadId changes
  useEffect(() => {
    threadIdRef.current = threadId;
  }, [threadId]);

  // Initialize the agent client
  useEffect(() => {
    // Create the agent client only once
    if (!agentClientRef.current) {
      agentClientRef.current = new AgentClient();
    }
  }, []);

  // Get the base URL dynamically in the browser
  const getBaseUrl = useCallback(() => {
    if (typeof window !== 'undefined') {
      return `${window.location.protocol}//${window.location.host}`;
    }
    return '';
  }, []);
  
  // Function to fetch scene history for the current thread
  const fetchSceneHistory = useCallback(async () => {
    if (!threadIdRef.current || !agentClientRef.current) return;
    
    try {
      const response = await agentClientRef.current.getSceneHistory(threadIdRef.current);
      
      if (response.history && Array.isArray(response.history)) {
        setSceneHistory(response.history);
        console.log(`Loaded ${response.history.length} scenes in history for thread ${threadIdRef.current}`);
      } else {
        console.log(`No scene history found for thread ${threadIdRef.current}`);
      }
    } catch (error) {
      console.error("Error fetching scene history:", error);
      // Don't set scene history to empty on error, maintain current value
    }
  }, []);
  
  // Function to fetch thread data
  const fetchThreadData = useCallback(async (currentThreadId: string) => {
    try {
      if (!agentClientRef.current) return;
      
      console.log(`Fetching thread data for thread: ${currentThreadId}`);
      const threadData = await agentClientRef.current.getThread(currentThreadId);
      
      // Update state
      if (threadData.messages && threadData.messages.length > 0) {
        // Convert AgentMessage to MessageType and track them for deduplication
        const convertedMessages = threadData.messages.map((msg: AgentMessage): MessageType => ({
          id: msg.id,
          type: msg.type,
          content: msg.content,
          metadata: msg.metadata
        }));
        
        // Track all messages to prevent duplicates
        convertedMessages.forEach(msg => {
          messageIdsRef.current.add(msg.id);
          
          if (msg.type === 'human') {
            humanMessageContentsRef.current.add(msg.content);
          } else {
            aiMessageContentsRef.current.set(msg.content, true);
          }
        });
        
        setMessages(convertedMessages);
        console.log(`Loaded ${convertedMessages.length} messages for thread ${currentThreadId}`);
      }
      
      if (threadData.signedUrl) {
        console.log("Setting signed URL from thread data:", threadData.signedUrl.substring(0, 50) + "...");
        setSignedUrl(threadData.signedUrl);
      }
      
      if (threadData.status) {
        setStatus(threadData.status);
      }
      
      // Update scene state if available
      if (threadData.sceneState) {
        console.log(`Setting scene state for thread ${currentThreadId} to ${threadData.sceneState.id}`);
        setSceneState(threadData.sceneState);
      }
      
      // Update scene history if available
      if (threadData.sceneHistory) {
        console.log(`Setting scene history with ${threadData.sceneHistory.length} scenes`);
        setSceneHistory(threadData.sceneHistory);
      } else {
        // If no scene history in thread data, try to fetch it directly
        fetchSceneHistory();
      }
    } catch (error) {
      console.error("Error fetching thread data:", error);
    }
  }, [fetchSceneHistory]);
  
  // Effect to load thread from localStorage on first mount
  useEffect(() => {
    const savedThreadId = localStorage.getItem('animationThreadId');
    if (savedThreadId) {
      console.log(`Loaded thread ID from localStorage: ${savedThreadId}`);
      setThreadId(savedThreadId);
      threadIdRef.current = savedThreadId;
      
      // Fetch the thread data
      fetchThreadData(savedThreadId).catch(console.error);
    } else {
      console.log("No thread ID found in localStorage");
    }
  }, [fetchThreadData]);
  
  // Helper to check if a message is a duplicate
  const isDuplicateMessage = useCallback((id: string, content: string, type: string): boolean => {
    // Check if we've seen this ID before
    if (messageIdsRef.current.has(id)) {
      return true;
    }
    
    // For human messages, check content exactly
    if (type === 'human') {
      if (humanMessageContentsRef.current.has(content)) {
        return true;
      }
    }
    // For AI messages, do more sophisticated checking
    else if (type === 'ai') {
      // Check exact content match
      if (aiMessageContentsRef.current.has(content)) {
        return true;
      }
      
      // Special check for generated animation message which might be repeated
      if (content.includes("Your animation is ready") && 
          Array.from(aiMessageContentsRef.current.keys()).some(
            existingContent => existingContent.includes("Your animation is ready"))) {
        return true;
      }
      
      // Special check for initialization messages
      if (currentPromptRef.current && 
          content.includes(`I'm generating a 3D animation based on your request: '${currentPromptRef.current}'`)) {
        return true;
      }
    }
    
    return false;
  }, []);
  
  // Process events from the stream
  const handleEvent = useCallback((event: AnimationCustomEvent) => {
    if (event.type) console.log("Received event:", event.type);
    
    switch (event.type) {
      case 'state': {
        // Use a block scope to avoid variable name conflicts
        const data = event.data;
        if (!data) break;
        
        const serverMessages = data.messages;
        if (!serverMessages || !Array.isArray(serverMessages)) break;
        
        // Don't completely replace messages; merge with existing ones
        setMessages(prevMessages => {
          // Start with current messages
          const existingMessages = [...prevMessages];
          const existingIds = new Set(existingMessages.map(msg => msg.id));
          
          // Add only new server messages
          const newMessages = [];
          for (const serverMsg of serverMessages) {
            if (!existingIds.has(serverMsg.id) && 
                !isDuplicateMessage(serverMsg.id, serverMsg.content, serverMsg.type)) {
              // Add to tracking sets
              messageIdsRef.current.add(serverMsg.id);
              
              if (serverMsg.type === 'human') {
                humanMessageContentsRef.current.add(serverMsg.content);
              } else {
                aiMessageContentsRef.current.set(serverMsg.content, true);
              }
              
              newMessages.push(serverMsg);
            }
          }
          
          return [...existingMessages, ...newMessages];
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
        
        // Skip if this message is a duplicate
        if (isDuplicateMessage(id, messageContent, messageType)) {
          console.log("Skipping duplicate message:", messageContent.substring(0, 50));
          return;
        }
        
        const messageData: MessageType = {
          id,
          type: messageType,
          content: messageContent,
          metadata: {
            sceneId: data.scene_id
          }
        };
        
        // Add to tracking sets
        messageIdsRef.current.add(id);
        if (messageType === 'human') {
          humanMessageContentsRef.current.add(messageContent);
        } else {
          aiMessageContentsRef.current.set(messageContent, true);
        }
        
        // Add the message to the UI
        setMessages(prev => [...prev, messageData]);
        break;
      }
        
      case 'data': {
        const data = event.data;
        if (!data) break;
        
        // Check multiple possible URL field names
        const url = data.signed_url || data.signedUrl;
        if (url) {
          console.log("Received signed URL in data event:", url.substring(0, 50) + "...");
          setSignedUrl(url);
        }
        
        // Check for scene data
        if (data.scene_id) {
          console.log("Received scene_id:", data.scene_id);
        }
        break;
      }
        
      case 'scene_state': {
        const data = event.data;
        if (!data || !data.scene_state) break;
        
        setSceneState(data.scene_state as SceneState);
        break;
      }
        
      case 'scene_history': {
        const data = event.data;
        if (!data || !data.scene_history) break;
        
        setSceneHistory(data.scene_history as SceneState[]);
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
  }, [isDuplicateMessage]);
  
  // Function to create a thread and stream events
  const generateAnimation = useCallback(async (prompt: string) => {
    setIsError(false);
    setErrorMessage('');
    setStatus('Processing your request...');
    setIsLoading(true);
    
    // Check if this is a duplicate human message
    if (humanMessageContentsRef.current.has(prompt)) {
      console.log("Detected duplicate human prompt:", prompt);
      // We'll still process it, but ensure we don't add it again to our messages state
    }
    
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
        content: `I'm working on your request: '${prompt}'. This might take a moment...`
      };
      
      // Add this prompt to our set of human messages so we don't duplicate it
      humanMessageContentsRef.current.add(prompt);
      
      // Track these messages to prevent duplicates
      messageIdsRef.current.add(humanMessage.id);
      messageIdsRef.current.add(initialMessage.id);
      aiMessageContentsRef.current.set(initialMessage.content, true);
      
      // Add human message only if it's not already in our messages list
      setMessages(prevMessages => {
        // Check if the exact content already exists in our message list
        const promptExists = prevMessages.some(msg => 
          msg.type === 'human' && msg.content === prompt
        );
        
        if (promptExists) {
          // Only add the AI processing message
          return [...prevMessages, initialMessage];
        } else {
          // Add both human and AI message
          return [...prevMessages, humanMessage, initialMessage];
        }
      });
      
      // IMPORTANT: Use the current threadId from the ref, not the state
      // This ensures we're using the latest value
      const currentThreadId = threadIdRef.current;
      
      // Create a new thread or use existing one
      const endpoint = currentThreadId 
        ? `${getBaseUrl()}/api/thread/${currentThreadId}` 
        : `${getBaseUrl()}/api/thread/new`;
      
      console.log(`Sending request to: ${endpoint} with thread ID: ${currentThreadId || 'new'}`);
      
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
      
      // Check for threadId in response headers
      const responseThreadId = response.headers.get('X-Thread-ID');
      const locationHeader = response.headers.get('Location');
      
      // If this is a new thread or we don't have a thread ID yet, save the thread ID
      if (!currentThreadId || currentThreadId === 'new') {
        // First try to get it from the X-Thread-ID header
        let newThreadId: string | null = responseThreadId;
        
        // If not available, try Location header
        if (!newThreadId && locationHeader) {
          const locationParts = locationHeader.split('/');
          newThreadId = locationParts[locationParts.length - 1];
        } else if (!newThreadId && response.url) {
          // Fallback to the URL
          const urlParts = response.url.split('/');
          newThreadId = urlParts[urlParts.length - 1];
        }
        
        if (newThreadId && newThreadId !== 'new') {
          console.log(`Setting thread ID to: ${newThreadId}`);
          setThreadId(newThreadId);
          threadIdRef.current = newThreadId;
          // Save to localStorage for persistence across refreshes
          localStorage.setItem('animationThreadId', newThreadId);
        } else {
          console.warn("Could not determine thread ID from response");
        }
      } else {
        console.log(`Using existing thread ID: ${currentThreadId}`);
      }
      
      // Handle streaming response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Failed to get response reader");
      }
      
      const decoder = new TextDecoder();
      let buffer = "";
      
      console.log("Started reading response stream");
      
      // Process the stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("Response stream ended");
          break;
        }
        
        const chunk = decoder.decode(value, { stream: true });
        console.log(`Received chunk: ${chunk.length} characters`);
        
        buffer += chunk;
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        
        console.log(`Processing ${lines.length} events`);
        
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
      
      console.log("Completed processing animation stream");
      console.log("Final signedUrl:", signedUrl ? signedUrl.substring(0, 20) + "..." : "Not present");
      console.log("Final threadId:", threadIdRef.current);
      
      // Fetch scene history after animation is generated
      if (threadIdRef.current) {
        setTimeout(() => {
          fetchSceneHistory();
        }, 500);
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
      const errorMessage: MessageType = {
        id: uuidv4(),
        type: 'ai',
        content: "Sorry, there was an error generating the animation. You can try another prompt if you'd like."
      };
      
      // Only add if not a duplicate
      if (!isDuplicateMessage(errorMessage.id, errorMessage.content, errorMessage.type)) {
        messageIdsRef.current.add(errorMessage.id);
        aiMessageContentsRef.current.set(errorMessage.content, true);
        
        setMessages(prev => [...prev, errorMessage]);
      }
    }
  }, [handleEvent, getBaseUrl, signedUrl, isDuplicateMessage, fetchSceneHistory]);
  
  // Function to stop the generation
  const stopGeneration = useCallback(() => {
    setIsLoading(false);
    currentPromptRef.current = null;
    
    // Add a message indicating the generation was stopped
    const stoppedMessage: MessageType = {
      id: uuidv4(),
      type: 'ai',
      content: "The animation generation was interrupted. You can try another prompt if you'd like."
    };
    
    // Only add if not a duplicate
    if (!isDuplicateMessage(stoppedMessage.id, stoppedMessage.content, stoppedMessage.type)) {
      messageIdsRef.current.add(stoppedMessage.id);
      aiMessageContentsRef.current.set(stoppedMessage.content, true);
      
      setMessages(prev => [...prev, stoppedMessage]);
    }
  }, [isDuplicateMessage]);
  
  // Function to clear chat history and start a new conversation
  const clearConversation = useCallback(async () => {
    console.log("Clearing conversation and thread data");
    
    try {
      // If we have an existing thread ID, tell the server to delete it
      if (threadIdRef.current) {
        try {
          await fetch(`${getBaseUrl()}/api/thread/${threadIdRef.current}`, {
            method: 'DELETE',
          });
          console.log(`Deleted thread ${threadIdRef.current} on the server`);
        } catch (err) {
          console.error("Error deleting thread on server:", err);
          // Continue with local cleanup even if server deletion fails
        }
      }
      
      setMessages([]);
      setSignedUrl(null);
      setStatus('');
      setIsError(false);
      setErrorMessage('');
      
      // Important: Clear thread ID in both state and ref
      setThreadId(null);
      threadIdRef.current = null;
      currentPromptRef.current = null;
      
      // Clear message tracking
      messageIdsRef.current.clear();
      humanMessageContentsRef.current.clear();
      aiMessageContentsRef.current.clear();
      
      // Remove from localStorage
      localStorage.removeItem('animationThreadId');
      
      // Clear scene state
      setSceneState(undefined);
      setSceneHistory([]);
      
      console.log("Conversation and thread data cleared");
    } catch (error) {
      console.error("Error during conversation clearing:", error);
    }
  }, [getBaseUrl]);
  
  // Function to analyze edits using the AgentClient
  const analyzeSceneEdit = useCallback(async (prompt: string) => {
    if (!sceneState || !agentClientRef.current) return null;
    
    try {
      const conversationHistory = messages.map(msg => ({
        role: msg.type,
        content: msg.content
      }));
      
      const response = await agentClientRef.current.analyzeSceneEdit(
        prompt,
        sceneState,
        threadIdRef.current || undefined,
        conversationHistory
      );
      
      return response.edit_instructions;
    } catch (error) {
      console.error("Error analyzing scene edit:", error);
      return null;
    }
  }, [sceneState, messages]);
  
  // Effect to fetch scene history when threadId changes
  useEffect(() => {
    if (threadId) {
      fetchSceneHistory();
    }
  }, [threadId, fetchSceneHistory]);
  
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
    sceneState,
    sceneHistory,
    fetchSceneHistory,
    analyzeSceneEdit
  };
}