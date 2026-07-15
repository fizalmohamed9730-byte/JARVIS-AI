import axios from 'axios';
import toast from 'react-hot-toast';

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jarvis_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.detail || error.response?.data?.message || error.message;
    if (error.response?.status === 401) {
      localStorage.removeItem('jarvis_token');
      window.location.href = '/';
    } else if (error.response?.status >= 500) {
      toast.error(`Server error: ${msg}`);
    }
    return Promise.reject(error);
  },
);
