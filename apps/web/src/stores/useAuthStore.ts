import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '@/types/models';

interface AuthStore {

  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User) => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
}

/**
 * Auth Store using Zustand
 * Manages user profile and authentication status.
 * Note: Since we use HTTP Only Cookies, the actual token is managed by the browser.
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      setAuth: (user) => 
        set({ 
          user, 
          isAuthenticated: true, 
          isLoading: false 
        }),

      clearAuth: () => 
        set({ 
          user: null, 
          isAuthenticated: false, 
          isLoading: false 
        }),

      setLoading: (loading) => 
        set({ 
          isLoading: loading 
        }),
    }),
    {
      name: 'auth-storage',
      // Persist only user and isAuthenticated status
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);
