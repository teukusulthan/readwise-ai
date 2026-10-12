import env from '@/config/env';
import axios, { AxiosError, AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { API_ENDPOINTS } from './api-endpoints';
import { toApiError } from './api-error';
import { handleSessionExpired } from './session-expiry';

/**
 * API Client instance with Axios
 * Handles base configuration, request/response interceptors, and error handling for HTTP Only Cookies.
 */

// Flag and queue for handling multiple 401 errors
let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

const apiClient: AxiosInstance = axios.create({
  baseURL: env.api.baseUrl,
  timeout: 30000,
  withCredentials: true, // Crucial for HTTP Only Cookies
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

/**
 * Ask the backend for new auth cookies (it reads the HttpOnly `refresh_token` cookie and sets new `token` /
 * `refresh_token` cookies). Bare axios, not apiClient, so a failing refresh can't recurse into the interceptor.
 * Also used by the SSE client, which does not go through axios.
 */
export async function refreshSession(): Promise<void> {
  await axios.get(API_ENDPOINTS.AUTH.REFRESH, { baseURL: env.api.baseUrl, withCredentials: true });
}

// Request Interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Note: With HTTP Only Cookies (token & refresh_token), 
    // the browser automatically attaches cookies to the request.
    // Manual Authorization header setting is typically not needed 
    // unless your backend requires both.
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response Interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const { response } = error;

    // Handle Unauthorized errors (401) and ensure we don't loop
    if (response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, add original request to queue
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            // Browser will automatically use the new cookies from the refresh response
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await refreshSession();

        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);

        // Forget the user (and, with VITE_AUTH_ENABLED, go to /login?next=<current page>).
        handleSessionExpired();

        return Promise.reject(toApiError(error));
      } finally {
        isRefreshing = false;
      }
    }

    // Standardize: always reject with an Error carrying the backend's message.
    return Promise.reject(toApiError(error));
  }
);

export default apiClient;

