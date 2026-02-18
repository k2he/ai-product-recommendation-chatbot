import { useState, useCallback } from 'react';
import { chatAPI } from '../services/api';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  const sendMessage = useCallback(async (query) => {
    setLoading(true);
    setError(null);

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await chatAPI.sendMessage(query, conversationId);

      // Update conversation ID
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      // Add assistant message
      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.message,
        products: response.products || [],
        hasResults: response.has_results,
        source: response.source,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      return response;
    } catch (err) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  const executeAction = useCallback(async (action, productId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await chatAPI.executeAction(action, productId, conversationId);

      // Add action result message
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
