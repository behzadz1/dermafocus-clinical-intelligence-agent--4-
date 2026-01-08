import { GoogleGenAI, Chat, GenerateContentResponse } from "@google/genai";
import { SYSTEM_INSTRUCTION } from '../constants';

let chatSession: Chat | null = null;

export const initializeChat = async (): Promise<Chat> => {
  if (chatSession) return chatSession;

  if (!process.env.API_KEY) {
    console.warn("API_KEY is missing from environment variables.");
    throw new Error("API Key missing");
  }

  // Initialize with the recommended model for clinical intelligence tasks
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  
  chatSession = ai.chats.create({
    model: 'gemini-3-flash-preview',
    config: {
      systemInstruction: SYSTEM_INSTRUCTION,
      temperature: 0.2, // Low temperature for factual, medical adherence
      topK: 40,
    },
  });

  return chatSession;
};

export const sendMessageToGemini = async (message: string): Promise<AsyncIterable<GenerateContentResponse>> => {
  const chat = await initializeChat();
  return chat.sendMessageStream({ message });
};

export const resetSession = () => {
  chatSession = null;
}