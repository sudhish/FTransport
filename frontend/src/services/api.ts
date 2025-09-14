import axios from 'axios';
import { Transfer, CreateTransferRequest, URLValidationResponse, FileTransfer } from '../types/index.ts';
import { apiLogger } from '../utils/logger.ts';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  apiLogger.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Log responses and handle errors
apiClient.interceptors.response.use(
  (response) => {
    apiLogger.debug(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    const url = error.config?.url || 'unknown';
    const status = error.response?.status || 'no response';
    const message = error.response?.data?.detail || error.message;
    apiLogger.error(`API Error: ${status} ${url} - ${message}`);
    return Promise.reject(error);
  }
);

export const api = {
  // Auth endpoints
  login: async () => {
    const response = await apiClient.post('/api/auth/login');
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/api/auth/logout');
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  },

  // Transfer endpoints
  createTransfer: async (data: CreateTransferRequest): Promise<Transfer> => {
    const response = await apiClient.post('/api/transfers/', data);
    return response.data;
  },

  listTransfers: async (): Promise<Transfer[]> => {
    const response = await apiClient.get('/api/transfers/');
    return response.data;
  },

  getTransfer: async (transferId: string): Promise<Transfer> => {
    const response = await apiClient.get(`/api/transfers/${transferId}`);
    return response.data;
  },

  getTransferFiles: async (transferId: string): Promise<FileTransfer[]> => {
    const response = await apiClient.get(`/api/transfers/${transferId}/files`);
    return response.data;
  },

  cancelTransfer: async (transferId: string) => {
    const response = await apiClient.delete(`/api/transfers/${transferId}`);
    return response.data;
  },

  clearCompletedTransfers: async () => {
    const response = await apiClient.delete('/api/transfers/');
    return response.data;
  },

  getTransferStatus: async (transferId: string) => {
    const response = await apiClient.get(`/api/transfers/${transferId}/status`);
    return response.data;
  },

  validateUrl: async (url: string): Promise<URLValidationResponse> => {
    const response = await apiClient.post('/api/transfers/validate-url', { url });
    return response.data;
  },

  // Health endpoint
  healthCheck: async () => {
    const response = await apiClient.get('/api/health');
    return response.data;
  },
};