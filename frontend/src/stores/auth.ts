import { defineStore } from 'pinia';
import type { User, AuthState, LoginResponse, TokenResponse } from '@/types';

const TOKEN_KEY = 'auth_access_token';
const REFRESH_KEY = 'auth_refresh_token';
const USER_KEY = 'auth_user';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: (() => {
      try {
        const raw = localStorage.getItem(USER_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch {
        localStorage.removeItem(USER_KEY);
        return null;
      }
    })(),
    accessToken: localStorage.getItem(TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_KEY),
    isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
    isLoading: false,
  }),

  getters: {
    currentUser: (state) => state.user,
    token: (state) => state.accessToken,
  },

  actions: {
    /** 登录 */
    async login(username: string, password: string) {
      this.isLoading = true;
      try {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || '登录失败');
        }
        const data: LoginResponse = await res.json();
        this.setAuth(data);
        return data;
      } finally {
        this.isLoading = false;
      }
    },

    /** 注册 */
    async register(username: string, password: string, nickname?: string) {
      this.isLoading = true;
      try {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password, nickname }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || '注册失败');
        }
        const data: LoginResponse = await res.json();
        this.setAuth(data);
        return data;
      } finally {
        this.isLoading = false;
      }
    },

    /** 登出 */
    async logout() {
      try {
        if (this.accessToken) {
          await fetch(`${API_BASE}/api/auth/logout`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${this.accessToken}` },
          }).catch(() => { });
        }
      } finally {
        this.clearAuth();
      }
    },

    /** 刷新 Token */
    async refreshAccessToken() {
      if (!this.refreshToken) {
        this.clearAuth();
        return false;
      }
      try {
        const res = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });
        if (!res.ok) {
          this.clearAuth();
          return false;
        }
        const data: TokenResponse = await res.json();
        this.accessToken = data.access_token;
        localStorage.setItem(TOKEN_KEY, data.access_token);
        return true;
      } catch {
        this.clearAuth();
        return false;
      }
    },

    /** 获取当前用户信息 */
    async fetchUser() {
      if (!this.accessToken) return;
      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${this.accessToken}` },
        });
        if (res.ok) {
          const user: User = await res.json();
          this.user = user;
          localStorage.setItem(USER_KEY, JSON.stringify(user));
        } else if (res.status === 401) {
          const refreshed = await this.refreshAccessToken();
          if (refreshed) await this.fetchUser();
        }
      } catch {
        // 静默失败
      }
    },

    /** 设置认证信息 */
    setAuth(data: LoginResponse) {
      this.accessToken = data.access_token;
      this.refreshToken = data.refresh_token;
      this.user = data.user;
      this.isAuthenticated = true;
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(REFRESH_KEY, data.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    },

    /** 清除认证信息 */
    clearAuth() {
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      this.isAuthenticated = false;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      localStorage.removeItem(USER_KEY);
    },
  },
});
