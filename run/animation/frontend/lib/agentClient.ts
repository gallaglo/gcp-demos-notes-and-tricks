import { v4 as uuidv4 } from 'uuid';
import { fetchWithRetry, RetryContext } from './utils';
import { SceneState } from './types/scene';

// Types
export interface Message {
  id: string;
  type: 'human' | 'ai';
  content: string;
  metadata?: {
    sceneId?: string;
    modifiedObjects?: string[];
    action?: 'create' | 'modify' | 'delete';
  };
}

export interface ThreadResponse {
  messages: Message[];
  signedUrl?: string;
  status: string;
  error?: string;
  sceneState?: SceneState;
  sceneHistory?: SceneState[];
}

export interface GenerateOptions {
  threadId?: string;
  onRetry?: (context: RetryContext) => void;
}

/**
 * Class to handle communication with the animation agent API
 */
export class AgentClient {
  private baseUrl: string;
  
  constructor(baseUrl?: string) {
    // Use the provided baseUrl or default to relative path
    this.baseUrl = baseUrl || (typeof window !== 'undefined' 
      ? `${window.location.protocol}//${window.location.host}/api`
      : '/api');
  }
  
  /**
   * Generate an animation via the thread API
   */
  async generateAnimation(prompt: string, options: GenerateOptions = {}): Promise<ThreadResponse> {
    try {
      const { threadId, onRetry } = options;
      
      // Determine the endpoint - thread/new or an existing thread
      const endpoint = threadId 
        ? `${this.baseUrl}/thread/${threadId}`
        : `${this.baseUrl}/thread/new`;
      
      console.log(`Sending animation request to ${endpoint}`);
      
      // Create a message object
      const message: Message = {
        id: uuidv4(),
        type: 'human',
        content: prompt
      };
      
      // Make the request to the thread API
      const response = await fetchWithRetry(
        endpoint,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            messages: [message]
          })
        },
        {
          maxAttempts: 3,
          initialDelay: 2000
        },
        onRetry
      );
      
      // Parse and return the response
      const data = await response.json();
      return data as ThreadResponse;
      
    } catch (error) {
      console.error('Error generating animation:', error);
      throw error;
    }
  }
  
  /**
   * Get the state of a thread
   */
  async getThread(threadId: string): Promise<ThreadResponse> {
    try {
      const response = await fetchWithRetry(
        `${this.baseUrl}/thread/${threadId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        },
        {
          maxAttempts: 2,
          initialDelay: 1000
        }
      );
      
      const data = await response.json();
      return data as ThreadResponse;
      
    } catch (error) {
      console.error('Error getting thread:', error);
      throw error;
    }
  }
  
  /**
   * Get the scene history for a thread
   */
  async getSceneHistory(threadId: string): Promise<{ history: SceneState[], success: boolean }> {
    try {
      const response = await fetchWithRetry(
        `${this.baseUrl}/scene-history/${threadId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      return await response.json();
      
    } catch (error) {
      console.error('Error getting scene history:', error);
      throw error;
    }
  }
  
  /**
   * Analyze a scene edit request
   */
  async analyzeSceneEdit(
    prompt: string, 
    sceneState: SceneState, 
    threadId?: string, 
    conversationHistory?: { role: string, content: string }[]
  ) {
    try {
      // Use the analyze-edit endpoint as defined in the backend API
      const response = await fetchWithRetry(
        `${this.baseUrl}/analyze-edit`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            prompt,
            scene_state: sceneState,
            thread_id: threadId,
            conversation_history: conversationHistory
          })
        }
      );
      
      return await response.json();
      
    } catch (error) {
      console.error('Error analyzing scene edit:', error);
      throw error;
    }
  }
}