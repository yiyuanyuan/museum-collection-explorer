import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token if needed
api.interceptors.request.use(
  (config) => {
    // Add auth token here if needed
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.data);
    } else if (error.request) {
      // Request was made but no response
      console.error('Network Error:', error.request);
    } else {
      // Something else happened
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// ============ CHAT API FUNCTIONS ============

/**
 * Send a chat message with optional image
 * @param {string} message - Text message
 * @param {object} context - Context object with session_id
 * @param {string} imageData - Base64 encoded image data (optional)
 */
export const sendChatMessage = async (message, context = {}, imageData = null) => {
  try {
    const payload = {
      message: message || '',
      session_id: context.session_id || 'default'
    };
    
    // Add image data if provided
    if (imageData) {
      // Remove data URL prefix if present
      const base64Data = imageData.includes(',') 
        ? imageData.split(',')[1] 
        : imageData;
      payload.image = base64Data;
    }
    
    const response = await api.post('/chat', payload);
    return response.data;

  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

/**
 * Get chat suggestions
 */
export const getChatSuggestions = async () => {
  try {
    const response = await api.get('/chat/suggestions');
    return response.data;
  } catch (error) {
    console.error('Error getting chat suggestions:', error);
    throw error;
  }
};

/**
 * Clear chat history for a session
 * @param {string} sessionId - Session ID (optional)
 */
export const clearChatHistory = async (sessionId = null) => {
  try {
    const response = await api.post('/chat/clear', {
      session_id: sessionId
    });
    return response.data;
  } catch (error) {
    console.error('Error clearing chat history:', error);
    throw error;
  }
};

/**
 * Get chat history for a session
 * @param {string} sessionId - Session ID (optional)
 */
export const getChatHistory = async (sessionId = null) => {
  try {
    const params = sessionId ? { session_id: sessionId } : {};
    const response = await api.get('/chat/history', { params });
    return response.data;
  } catch (error) {
    console.error('Error getting chat history:', error);
    throw error;
  }
};

// ============ BIOCACHE/MAP API FUNCTIONS ============

/**
 * Fetch occurrences from the biocache
 * @param {object} params - Query parameters
 */
export const fetchOccurrences = async (params = {}) => {
  try {
    const response = await api.get('/occurrences', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching occurrences:', error);
    throw error;
  }
};

/**
 * Fetch statistics from the biocache
 */
export const fetchStatistics = async () => {
  try {
    const response = await api.get('/statistics');
    return response.data;
  } catch (error) {
    console.error('Error fetching statistics:', error);
    throw error;
  }
};

// ============ HEALTH CHECK ============

/**
 * Check API health status
 */
export const checkHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
};

// Export the axios instance for direct use if needed
export default api;