import { defineStore } from 'pinia';
import axios from 'axios';

export const useUserStore = defineStore('user', {
  state: () => ({
    userId: null as string | null,
    name: null as string | null,
    role: 'user' as string,
    token: null as string | null,  // JWT access token
    refreshToken: null as string | null,  // JWT refresh token
  }),
  getters: {
    isAdmin: (state) => state.role === 'admin',
  },
  actions: {
    setUser(data: { userId: string; name: string; role?: string; token?: string; refreshToken?: string }) {
      this.userId = data.userId;
      this.name = data.name;
      if (data.role) {
        this.role = data.role;
      }
      if (data.token) {
        this.token = data.token;
      }
      if (data.refreshToken) {
        this.refreshToken = data.refreshToken;
      }
    },
    setToken(token: string) {
      this.token = token;
    },
    setRole(role: string) {
      this.role = role;
    },
    logout() {
      this.userId = null;
      this.name = null;
      this.role = 'user';
      this.token = null;
      this.refreshToken = null;
    },
    /**
     * 使用 refresh_token 获取新的 access_token
     * @returns 是否刷新成功
     */
    async refreshAccessToken(): Promise<boolean> {
      if (!this.refreshToken) {
        return false;
      }

      try {
        const { data } = await axios.post(
          `${import.meta.env.VITE_API_URL}/users/token/refresh`,
          { refresh_token: this.refreshToken },
          { headers: { 'Content-Type': 'application/json' } }
        );

        this.token = data.access_token;
        this.refreshToken = data.refresh_token;
        return true;
      } catch (error) {
        // refresh_token 也失效了，需要重新登录
        console.error('Token refresh failed:', error);
        this.logout();
        return false;
      }
    },
  },
  persist: true, // Keep user logged in across page reloads
});
