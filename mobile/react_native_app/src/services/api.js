import axios from 'axios';

// Configure API endpoint - update to match your Python Flask server
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  // Dashboard endpoints
  getVideoFeed: () => `${API_BASE_URL}/video_feed`,
  
  getCurrentState: async () => {
    try {
      const response = await api.get('/api/state');
      return response.data;
    } catch (error) {
      console.error('Error fetching current state:', error);
      throw error;
    }
  },

  getHistory: async (limit = 50) => {
    try {
      const response = await api.get('/api/history', { params: { limit } });
      return response.data;
    } catch (error) {
      console.error('Error fetching history:', error);
      throw error;
    }
  },

  getSnapshots: async () => {
    try {
      const response = await api.get('/api/snapshots');
      return response.data;
    } catch (error) {
      console.error('Error fetching snapshots:', error);
      throw error;
    }
  },

  // Control endpoints
  updateConfig: async (config) => {
    try {
      const response = await api.post('/api/config', config);
      return response.data;
    } catch (error) {
      console.error('Error updating config:', error);
      throw error;
    }
  },

  getConfig: async () => {
    try {
      const response = await api.get('/api/config');
      return response.data;
    } catch (error) {
      console.error('Error fetching config:', error);
      throw error;
    }
  },

  setCameraEnabled: async (enabled) => {
    try {
      const response = await api.post('/api/camera', { enabled });
      return response.data;
    } catch (error) {
      console.error('Error toggling camera:', error);
      throw error;
    }
  },

  setConfidenceThreshold: async (threshold) => {
    try {
      const response = await api.post('/api/threshold', { threshold });
      return response.data;
    } catch (error) {
      console.error('Error setting threshold:', error);
      throw error;
    }
  },

  takeSnapshot: async () => {
    try {
      const response = await api.post('/api/snapshot');
      return response.data;
    } catch (error) {
      console.error('Error taking snapshot:', error);
      throw error;
    }
  },

  getReportData: async (startDate, endDate) => {
    try {
      const response = await api.get('/api/report', {
        params: { start_date: startDate, end_date: endDate }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching report data:', error);
      throw error;
    }
  },
};

export default api;
