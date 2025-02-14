import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export interface RetryConfig {
  maxAttempts?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffFactor?: number;
  retryableStatuses?: number[];
}

export interface RetryContext {
  attempt: number;
  error: Error | null;
  maxAttempts: number;
}

const defaultConfig: RetryConfig = {
  maxAttempts: 3,
  initialDelay: 1000, // 1 second
  maxDelay: 10000, // 10 seconds
  backoffFactor: 2,
  retryableStatuses: [408, 429, 500, 502, 503, 504]
};

export async function retryWithBackoff<T>(
  operation: () => Promise<T>,
  config: RetryConfig = {},
  onRetry?: (context: RetryContext) => void
): Promise<T> {
  const finalConfig = { ...defaultConfig, ...config };
  let lastError: Error | null = null;
  
  for (let attempt = 1; attempt <= finalConfig.maxAttempts!; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      // Check if the error is a Response with a status
      if (error instanceof Response) {
        if (!finalConfig.retryableStatuses!.includes(error.status)) {
          throw error;
        }
      }
      
      // Notify caller of retry attempt
      if (onRetry) {
        onRetry({
          attempt,
          error: lastError,
          maxAttempts: finalConfig.maxAttempts!
        });
      }
      
      // Don't wait on the last attempt
      if (attempt === finalConfig.maxAttempts) {
        break;
      }
      
      // Calculate delay with exponential backoff
      const delay = Math.min(
        finalConfig.initialDelay! * Math.pow(finalConfig.backoffFactor!, attempt - 1),
        finalConfig.maxDelay!
      );
      
      // Add some jitter to prevent thundering herd
      const jitter = Math.random() * 200;
      await new Promise(resolve => setTimeout(resolve, delay + jitter));
    }
  }
  
  throw lastError || new Error('Operation failed after all retry attempts');
}

export async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  retryConfig?: RetryConfig,
  onRetry?: (context: RetryContext) => void
): Promise<Response> {
  return retryWithBackoff(
    async () => {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw response;
      }
      return response;
    },
    retryConfig,
    onRetry
  );
}
