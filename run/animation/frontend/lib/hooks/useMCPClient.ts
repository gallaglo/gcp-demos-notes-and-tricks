import { useEffect, useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export interface AnimationData {
  signed_url: string;
  expiration?: string;
}

export function useMCPClient() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [animationData, setAnimationData] = useState<AnimationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load messages from localStorage on mount
  useEffect(() => {
    try {
      const savedMessages = localStorage.getItem('chat-messages');
      const savedAnimation = localStorage.getItem('animation-data');
      
      if (savedMessages) {
        setMessages(JSON.parse(savedMessages));
      }
      
      if (savedAnimation) {
        setAnimationData(JSON.parse(savedAnimation));
      }
    } catch (e) {
      console.error('Error loading saved state:', e);
    }
  }, []);

  // Save messages to localStorage when they change
  useEffect(() => {
    localStorage.setItem('chat-messages', JSON.stringify(messages));
  }, [messages]);

  // Save animation data to localStorage when it changes
  useEffect(() => {
    if (animationData) {
      localStorage.setItem('animation-data', JSON.stringify(animationData));
    }
  }, [animationData]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);

    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage],
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      // Add assistant messages
      if (data.messages && Array.isArray(data.messages)) {
        const newMessages = data.messages.map((msg: any) => ({
          id: uuidv4(),
          role: msg.role as 'assistant',
          content: msg.content
        }));

        setMessages(prev => [...prev, ...newMessages]);
      }

      // Check for animation data
      if (data.animation?.signed_url) {
        setAnimationData({
          signed_url: data.animation.signed_url,
          expiration: data.animation.expiration || '15 minutes'
        });
      }
    } catch (e) {
      console.error('Error sending message:', e);
      setError(e instanceof Error ? e.message : 'An unknown error occurred');
      
      // Add error message
      setMessages(prev => [
        ...prev,
        {
          id: uuidv4(),
          role: 'assistant',
          content: `Sorry, there was an error processing your request: ${
            e instanceof Error ? e.message : 'Unknown error'
          }`
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setAnimationData(null);
    setError(null);
    localStorage.removeItem('chat-messages');
    localStorage.removeItem('animation-data');
  }, []);

  return {
    messages,
    isLoading,
    animationData,
    error,
    sendMessage,
    clearChat
  };
}