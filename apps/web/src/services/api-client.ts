import env from '@/config/env';
import { useAuthStore } from '@/stores/useAuthStore';
import axios, { AxiosError, AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { API_ENDPOINTS } from './api-endpoints';

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
        // Call refresh token endpoint with credentials
        // The server should read 'refresh_token' cookie and set new 'token' & 'refresh_token' cookies
        // Bare axios (not apiClient) so a failing refresh can't recurse into this interceptor.
        await axios.get(API_ENDPOINTS.AUTH.REFRESH, {
          baseURL: apiClient.defaults.baseURL,
          withCredentials: true
        });

        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        // If refresh fails, the server should ideally clear cookies via Set-Cookie
        processQueue(refreshError);

        // Clear auth state in store
        useAuthStore.getState().clearAuth();

        // Optional: Manual redirect if needed
        // window.location.href = '/auth/login';

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Standardize error structure
    // Backend failures arrive as a top-level `BaseResponseFailed` envelope (primary) or a plain `{ detail: string }`.
    // The legacy `{ detail: BaseResponseFailed }` shape is still read for back-compat.
    const body = response?.data as any;
    const detail = body?.detail;
    const errorMessage =
      detail?.metaData?.message ||
      (typeof detail === 'string' ? detail : undefined) ||
      body?.metaData?.message ||
      body?.message ||
      error.message ||
      'Something went wrong';

    return Promise.reject({
      ...error,
      message: errorMessage,
      status: response?.status,
    });
  }
);

export default apiClient;

