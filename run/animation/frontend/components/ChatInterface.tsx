'use client';

import { useState, useRef, useEffect } from 'react';
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowUp, StopCircle } from "lucide-react";
import { MessageType } from '@/lib/hooks/useAnimationStream';

interface ChatInterfaceProps {
  messages: MessageType[];
  isLoading: boolean;
  onSendMessageAction: (message: string) => void;
  onStopAction: () => void;
}

export default function ChatInterface({
  messages,
  isLoading,
  onSendMessageAction,
  onStopAction
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState('');
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current;
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  }, [messages]);

  // Focus textarea when component mounts
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const handleSendMessage = () => {
    if (inputValue.trim() && !isLoading) {
      onSendMessageAction(inputValue);
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <CardContent className="flex flex-col h-full p-4">
        {/* Message Display Area */}
        <ScrollArea 
          ref={scrollAreaRef}
          className="flex-1 pr-4"
          type="always"
        >
          <div className="flex flex-col gap-4 py-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'human' ? 'justify-end' : 'justify-start'}`}
              >
                <div className="flex items-start gap-3 max-w-[80%]">
                  {message.type === 'ai' && (
                    <Avatar className="mt-1">
                      <AvatarFallback className="bg-primary text-primary-foreground">AI</AvatarFallback>
                    </Avatar>
                  )}
                  
                  <div
                    className={`py-2 px-3 rounded-lg ${
                      message.type === 'human'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  </div>
                  
                  {message.type === 'human' && (
                    <Avatar className="mt-1">
                      <AvatarFallback className="bg-secondary">You</AvatarFallback>
                    </Avatar>
                  )}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-start gap-3">
                  <Avatar className="mt-1">
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
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="flex items-end gap-2 mt-4">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="min-h-[60px] flex-1 resize-none"
            disabled={isLoading}
          />
          <div className="flex flex-col gap-2">
            {isLoading ? (
              <Button
                variant="destructive"
                size="icon"
                onClick={onStopAction}
                className="h-[60px]"
              >
                <StopCircle className="h-5 w-5" />
              </Button>
            ) : (
              <Button
                variant="default"
                size="icon"
                onClick={handleSendMessage}
                disabled={inputValue.trim() === ''}
                className="h-[60px]"
              >
                <ArrowUp className="h-5 w-5" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}