import { createApp } from 'vue';
import { createPinia } from 'pinia';
import piniaPluginPersistedState from 'pinia-plugin-persistedstate';
import { router } from './router';
import axios from 'axios';
import { useUserStore } from './stores/user';
import { useChatStore } from './stores/chat';
import './style.css';
import App from './App.vue';

const pinia = createPinia();
pinia.use(piniaPluginPersistedState);

const app = createApp(App);
app.use(router);
app.use(pinia);

// Token 刷新锁：避免多个请求同时刷新 token
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach(callback => callback(token));
  refreshSubscribers = [];
}

function addRefreshSubscriber(callback: (token: string) => void) {
  refreshSubscribers.push(callback);
}

// axios 请求拦截器：自动附加 Authorization header
axios.interceptors.request.use(
  (config) => {
    const userStore = useUserStore();
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// axios 响应拦截器：统一处理 401 token 失效，自动刷新
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 如果是 401 错误且不是刷新请求本身，尝试刷新 token
    if (error.response?.status === 401 && !originalRequest._retry) {
      const userStore = useUserStore();
      const chatStore = useChatStore();

      // 如果没有 refresh_token，直接登出
      if (!userStore.refreshToken) {
        chatStore.resetStore();
        userStore.logout();
        // 根据当前页面决定跳转目标
        const isAdminRoute = window.location.pathname.startsWith('/admin');
        router.push(isAdminRoute ? '/admin' : '/');
        return Promise.reject(error);
      }

      // 如果正在刷新中，将请求加入队列等待
      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(axios(originalRequest));
          });
        });
      }

      // 开始刷新
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const success = await userStore.refreshAccessToken();
        if (success) {
          // 刷新成功，重试原请求
          originalRequest.headers.Authorization = `Bearer ${userStore.token}`;
          // 通知队列中的请求
          onRefreshed(userStore.token!);
          return axios(originalRequest);
        } else {
          // 刷新失败，登出
          chatStore.resetStore();
          userStore.logout();
          const isAdminRoute = window.location.pathname.startsWith('/admin');
          router.push(isAdminRoute ? '/admin' : '/');
          return Promise.reject(error);
        }
      } catch (refreshError) {
        // 刷新失败，登出
        chatStore.resetStore();
        userStore.logout();
        const isAdminRoute = window.location.pathname.startsWith('/admin');
        router.push(isAdminRoute ? '/admin' : '/');
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

app.mount('#app');
