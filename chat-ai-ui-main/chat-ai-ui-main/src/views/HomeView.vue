<script setup lang="ts">
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { useUserStore } from '../stores/user';
import { useRouter } from 'vue-router';
import robotImage from '../assets/robot.png';

const userStore = useUserStore();
const router = useRouter();

const name = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');
const isVisible = ref(false);
const isFocused = ref(false);

onMounted(() => {
  // 页面加载动画
  setTimeout(() => {
    isVisible.value = true;
  }, 100);
});

const loginUser = async () => {
  if (!name.value || !password.value) {
    error.value = '用户名和密码是必填项';
    return;
  }

  loading.value = true;
  error.value = '';

  try {
    const form = new URLSearchParams();
    form.append('username', name.value);
    form.append('password', password.value);

    const { data } = await axios.post(
      `${import.meta.env.VITE_API_URL}/users/token`,
      form,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );

    userStore.setUser({
      userId: data.username,
      name: data.username,
      token: data.access_token,
      refreshToken: data.refresh_token,
    });

    // 获取用户详细信息（包括角色）
    try {
      const userResp = await axios.get(`${import.meta.env.VITE_API_URL}/users/me`);
      if (userResp.data.role) {
        userStore.setRole(userResp.data.role);
      }
    } catch (e) {
      console.error('获取用户信息失败:', e);
    }

    router.push('/chat');
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '登录失败';
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="login-page__bg">
      <div class="login-page__circle login-page__circle--1"></div>
      <div class="login-page__circle login-page__circle--2"></div>
      <div class="login-page__circle login-page__circle--3"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card" :class="{ 'login-card--visible': isVisible }">
      <!-- Logo -->
      <div class="login-card__logo">
        <div class="login-card__logo-wrapper">
          <img :src="robotImage" alt="Logo" class="login-card__logo-img" />
        </div>
      </div>

      <!-- 标题 -->
      <h1 class="login-card__title">欢迎使用图灵 AI</h1>
      <p class="login-card__subtitle">智能问答，高效工作</p>

      <!-- 表单 -->
      <form class="login-card__form" @submit.prevent="loginUser">
        <div class="login-card__field">
          <label class="login-card__label" for="username">用户名</label>
          <div class="login-card__input-wrapper">
            <svg class="login-card__input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <input
              id="username"
              v-model="name"
              type="text"
              placeholder="请输入用户名"
              class="login-card__input"
              @keyup.enter="loginUser"
              @focus="isFocused = true"
              @blur="isFocused = false"
            />
          </div>
        </div>

        <div class="login-card__field">
          <label class="login-card__label" for="password">密码</label>
          <div class="login-card__input-wrapper">
            <svg class="login-card__input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            <input
              id="password"
              v-model="password"
              type="password"
              placeholder="请输入密码"
              class="login-card__input"
              @keyup.enter="loginUser"
            />
          </div>
        </div>

        <!-- 错误提示 -->
        <Transition name="error">
          <div v-if="error" class="login-card__error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{{ error }}</span>
          </div>
        </Transition>

        <!-- 登录按钮 -->
        <button
          type="submit"
          class="login-card__submit"
          :disabled="loading"
          :class="{ 'login-card__submit--loading': loading }"
        >
          <span v-if="!loading">开始对话</span>
          <span v-else class="login-card__submit-loading">
            <span></span>
            <span></span>
            <span></span>
          </span>
        </button>
      </form>

      <!-- 底部信息 -->
      <div class="login-card__footer">
        <p>默认账号: root / admin123</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg);
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.login-page__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-page__circle {
  position: absolute;
  border-radius: var(--radius-full);
  opacity: 0.5;
}

.login-page__circle--1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, var(--color-accent-subtle), transparent 70%);
  top: -200px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.login-page__circle--2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(240, 147, 251, 0.1), transparent 70%);
  bottom: -150px;
  left: -100px;
  animation: float 10s ease-in-out infinite reverse;
}

.login-page__circle--3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(102, 126, 234, 0.08), transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: float 12s ease-in-out infinite;
}

/* 登录卡片 */
.login-card {
  width: 100%;
  max-width: 420px;
  padding: var(--space-10);
  background-color: var(--color-bg-elevated);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-xl);
  position: relative;
  z-index: 1;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.login-card--visible {
  opacity: 1;
  transform: translateY(0);
}

/* Logo */
.login-card__logo {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-8);
}

.login-card__logo-wrapper {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-accent-subtle), rgba(240, 147, 251, 0.1));
  border-radius: var(--radius-2xl);
  animation: float 3s ease-in-out infinite;
}

.login-card__logo-img {
  width: 56px;
  height: 56px;
}

/* 标题 */
.login-card__title {
  font-family: var(--font-serif);
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-text);
  text-align: center;
  margin-bottom: var(--space-2);
}

.login-card__subtitle {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  text-align: center;
  margin-bottom: var(--space-8);
}

/* 表单 */
.login-card__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.login-card__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.login-card__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.login-card__input-wrapper {
  position: relative;
}

.login-card__input-icon {
  position: absolute;
  left: var(--space-4);
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
  transition: color var(--transition-fast);
}

.login-card__input {
  width: 100%;
  padding: var(--space-4) var(--space-4) var(--space-4) var(--space-12);
  background-color: var(--color-bg-secondary);
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  color: var(--color-text);
  transition: all var(--transition-fast);
  outline: none;
}

.login-card__input::placeholder {
  color: var(--color-text-tertiary);
}

.login-card__input:focus {
  background-color: var(--color-bg-elevated);
  border-color: var(--color-accent);
  box-shadow: 0 0 0 4px var(--color-accent-subtle);
}

.login-card__input:focus + .login-card__input-icon,
.login-card__input:focus ~ .login-card__input-icon {
  color: var(--color-accent);
}

/* 错误提示 */
.login-card__error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
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

.error-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.error-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 提交按钮 */
.login-card__submit {
  width: 100%;
  padding: var(--space-4);
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-dark));
  color: white;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  transition: all var(--transition-fast);
  box-shadow: 0 4px 16px rgba(74, 108, 247, 0.3);
  margin-top: var(--space-2);
}

.login-card__submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(74, 108, 247, 0.4);
}

.login-card__submit:active:not(:disabled) {
  transform: translateY(0);
}

.login-card__submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.login-card__submit--loading {
  pointer-events: none;
}

.login-card__submit-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.login-card__submit-loading span {
  width: 8px;
  height: 8px;
  background-color: white;
  border-radius: var(--radius-full);
  animation: bounce 1.4s ease-in-out infinite;
}

.login-card__submit-loading span:nth-child(1) {
  animation-delay: 0s;
}

.login-card__submit-loading span:nth-child(2) {
  animation-delay: 0.2s;
}

.login-card__submit-loading span:nth-child(3) {
  animation-delay: 0.4s;
}

/* 底部信息 */
.login-card__footer {
  margin-top: var(--space-6);
  text-align: center;
}

.login-card__footer p {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 响应式 */
@media (max-width: 480px) {
  .login-card {
    margin: var(--space-4);
    padding: var(--space-8);
  }
}
</style>
