import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach user ID to every request
api.interceptors.request.use(
  (config) => {
    const userId = localStorage.getItem('userId') || 'user_001';
    config.headers['X-User-ID'] = userId;
    return config;
  },
  (error) => Promise.reject(error)
);

// Global error logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const chatAPI = {
  /**
   * Send a chat message.
   * @param {string} query - User's message
   * @param {string|null} conversationId - Ongoing conversation ID
   * @param {string[]} lastProductIds - SKUs of products shown in the last response
   *   (used by the backend intent chain to detect email/purchase requests)
   */
  sendMessage: async (query, conversationId = null, lastProductIds = []) => {
    const response = await api.post('/chat', {
      query,
      conversation_id: conversationId,
      last_product_ids: lastProductIds,
    });
    return response.data;
  },

  executeAction: async (action, productId, conversationId = null) => {
    const response = await api.post('/actions', {
      action,
      product_id: productId,
      conversation_id: conversationId,
    });
    return response.data;
  },

  createUser: async (userData) => {
    const response = await api.post('/users', userData);
    return response.data;
  },

  getUser: async (userId) => {
    const response = await api.get(`/users/${userId}`);
    return response.data;
  },

  checkHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
