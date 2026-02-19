import { useState, useCallback } from 'react';
import { chatAPI } from '../services/api';

export const useChat = (userName = 'there') => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  // Track the SKUs of the most recent products shown to the user
  const [lastProductIds, setLastProductIds] = useState([]);

  const sendMessage = useCallback(async (query) => {
    setLoading(true);
    setError(null);

    // Add user message immediately
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    // Optimistic assistant "thinking" message shown before API responds
    const thinkingId = Date.now() + 1;
    const thinkingMessage = {
      id: thinkingId,
      type: 'thinking',
      content: `Alright ${userName}, let me help you with that. Give me a second! ⏳`,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage, thinkingMessage]);

    try {
      const response = await chatAPI.sendMessage(query, conversationId, lastProductIds);

      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      // Track the new product IDs for the next turn (for intent detection)
      const newProductIds = (response.products || []).map((p) => p.sku).filter(Boolean);
      if (newProductIds.length > 0) {
        setLastProductIds(newProductIds);
      }

      // Replace thinking message with real assistant response
      const assistantMessage = {
        id: thinkingId,
        type: 'assistant',
        content: response.message,
        products: response.products || [],
        hasResults: response.has_results,
        source: response.source,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) =>
        prev.map((m) => (m.id === thinkingId ? assistantMessage : m))
      );

      return response;
    } catch (err) {
      // Replace thinking message with error
      const errorMessage = {
        id: thinkingId,
        type: 'error',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) =>
        prev.map((m) => (m.id === thinkingId ? errorMessage : m))
      );
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [conversationId, lastProductIds, userName]);

  const executeAction = useCallback(async (action, productId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await chatAPI.executeAction(action, productId, conversationId);

      const resultMessage = {
        id: Date.now(),
        type: 'action_result',
        content: response.message,
        success: response.success,
        action: response.action,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, resultMessage]);

      return response;
    } catch (err) {
      const errorMessage = {
        id: Date.now(),
        type: 'error',
        content: `Failed to ${action} product. Please try again.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setLastProductIds([]);
    setError(null);
  }, []);

  return {
    messages,
    loading,
    error,
    sendMessage,
    executeAction,
    clearMessages,
  };
};
