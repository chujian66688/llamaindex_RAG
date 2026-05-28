<script setup lang="ts">
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { useUserStore } from '../stores/user';
import { useRouter } from 'vue-router';

const userStore = useUserStore();
const router = useRouter();

const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');
const isVisible = ref(false);

onMounted(() => {
  // 如果已经是管理员，直接跳转
  if (userStore.token && userStore.isAdmin) {
    router.push('/admin/users');
    return;
  }
  setTimeout(() => {
    isVisible.value = true;
  }, 100);
});

const login = async () => {
  if (!username.value || !password.value) {
    error.value = '请输入用户名和密码';
    return;
  }

  loading.value = true;
  error.value = '';

  try {
    const form = new URLSearchParams();
    form.append('username', username.value);
    form.append('password', password.value);

    const { data } = await axios.post(
      `${import.meta.env.VITE_API_URL}/users/token`,
      form,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );

    userStore.setUser({
      userId: data.username,
      name: data.username,
      token: data.access_token,
      refreshToken: data.refresh_token,
    });

    // 获取用户角色
    try {
      const userResp = await axios.get(`${import.meta.env.VITE_API_URL}/users/me`);
      if (userResp.data.role) {
        userStore.setRole(userResp.data.role);
      }

      // 检查是否是管理员
      if (userResp.data.role !== 'admin') {
        error.value = '该账号没有管理员权限';
        userStore.logout();
        return;
      }
    } catch (e) {
      error.value = '获取用户信息失败';
      userStore.logout();
      return;
    }

    router.push('/admin/users');
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '登录失败';
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="admin-login">
    <!-- 背景装饰 -->
    <div class="admin-login__bg">
      <div class="admin-login__circle admin-login__circle--1"></div>
      <div class="admin-login__circle admin-login__circle--2"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="admin-login__card" :class="{ 'admin-login__card--visible': isVisible }">
      <div class="admin-login__header">
        <div class="admin-login__icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
          </svg>
        </div>
        <h1 class="admin-login__title">后台管理</h1>
        <p class="admin-login__subtitle">请使用管理员账号登录</p>
      </div>

      <form class="admin-login__form" @submit.prevent="login">
        <div class="admin-login__field">
          <label>用户名</label>
          <div class="admin-login__input-wrapper">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <input
              v-model="username"
              type="text"
              placeholder="请输入用户名"
              @keyup.enter="login"
            />
          </div>
        </div>

        <div class="admin-login__field">
          <label>密码</label>
          <div class="admin-login__input-wrapper">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            <input
              v-model="password"
              type="password"
              placeholder="请输入密码"
              @keyup.enter="login"
            />
          </div>
        </div>

        <Transition name="error">
          <div v-if="error" class="admin-login__error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{{ error }}</span>
          </div>
        </Transition>

        <button
          type="submit"
          class="admin-login__submit"
          :disabled="loading"
        >
          <span v-if="!loading">登录</span>
          <span v-else class="admin-login__loading">
            <span></span>
            <span></span>
            <span></span>
          </span>
        </button>
      </form>

      <div class="admin-login__footer">
        <button class="admin-login__back" @click="router.push('/')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <span>返回首页</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg);
  position: relative;
  overflow: hidden;
}

.admin-login__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.admin-login__circle {
  position: absolute;
  border-radius: var(--radius-full);
  opacity: 0.5;
}

.admin-login__circle--1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(74, 108, 247, 0.1), transparent 70%);
  top: -150px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.admin-login__circle--2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(240, 147, 251, 0.08), transparent 70%);
  bottom: -150px;
  left: -100px;
  animation: float 10s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.admin-login__card {
  width: 100%;
  max-width: 400px;
  padding: var(--space-8);
  background-color: var(--color-bg-elevated);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-xl);
  position: relative;
  z-index: 1;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.admin-login__card--visible {
  opacity: 1;
  transform: translateY(0);
}

.admin-login__header {
  text-align: center;
  margin-bottom: var(--space-6);
}

.admin-login__icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--space-4);
  background: linear-gradient(135deg, var(--color-accent-subtle), rgba(240, 147, 251, 0.1));
  border-radius: var(--radius-xl);
  color: var(--color-accent);
}

.admin-login__title {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text);
  margin-bottom: var(--space-1);
}

.admin-login__subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.admin-login__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.admin-login__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.admin-login__field label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.admin-login__input-wrapper {
  position: relative;
}

.admin-login__input-wrapper svg {
  position: absolute;
  left: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
}

.admin-login__input-wrapper input {
  width: 100%;
  padding: var(--space-3) var(--space-3) var(--space-3) var(--space-10);
  background-color: var(--color-bg-secondary);
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--color-text);
  outline: none;
  transition: all var(--transition-fast);
}

.admin-login__input-wrapper input::placeholder {
  color: var(--color-text-tertiary);
}

.admin-login__input-wrapper input:focus {
  background-color: var(--color-bg-elevated);
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-subtle);
}

.admin-login__error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background-color: rgba(239, 68, 68, 0.08);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: var(--text-sm);
}

.error-enter-active {
  transition: all var(--transition-base) ease-out;
}

.error-leave-active {
  transition: all var(--transition-fast) ease-in;
}

.error-enter-from,
.error-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.admin-login__submit {
  width: 100%;
  padding: var(--space-3);
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-dark));
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  transition: all var(--transition-fast);
  box-shadow: 0 4px 16px rgba(74, 108, 247, 0.3);
  margin-top: var(--space-2);
}

.admin-login__submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(74, 108, 247, 0.4);
}

.admin-login__submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.admin-login__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.admin-login__loading span {
  width: 8px;
  height: 8px;
  background-color: white;
  border-radius: var(--radius-full);
  animation: bounce 1.4s ease-in-out infinite;
}

.admin-login__loading span:nth-child(1) { animation-delay: 0s; }
.admin-login__loading span:nth-child(2) { animation-delay: 0.2s; }
.admin-login__loading span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.admin-login__footer {
  margin-top: var(--space-6);
  text-align: center;
}

.admin-login__back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  transition: color var(--transition-fast);
}

.admin-login__back:hover {
  color: var(--color-accent);
}
</style>
