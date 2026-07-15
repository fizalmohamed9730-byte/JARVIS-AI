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

let authRedirecting = false;

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const hadToken = localStorage.getItem('jarvis_token');
      localStorage.removeItem('jarvis_token');
      if (hadToken && !authRedirecting) {
        authRedirecting = true;
        toast.error('Session expired. Please log in again.');
        window.location.href = '/auth';
      }
      return Promise.reject(error);
    }
    const msg = error.response?.data?.detail || error.response?.data?.message || error.message;
    if (error.response?.status >= 500) {
      toast.error(`Server error: ${msg}`);
    }
    return Promise.reject(error);
  },
);
