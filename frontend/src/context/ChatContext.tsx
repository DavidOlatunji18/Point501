import { createContext, useContext, useState, type ReactNode } from "react";
import type { ChatSource } from "../lib/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  isError?: boolean;
}

interface ChatContextValue {
  messages: ChatMessage[];
  setMessages: (update: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

// Lives above the router outlet (see App.tsx) so the conversation survives
// navigating away from and back to the Chat page - it only resets on an
// explicit "Clear" or a full page refresh.
export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  return (
    <ChatContext.Provider value={{ messages, setMessages }}>{children}</ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within a ChatProvider");
  return ctx;
}
