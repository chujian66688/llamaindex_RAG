<script setup lang="ts">
import { useUserStore } from '../stores/user';
import { useRouter } from 'vue-router';
import robotImage from '../assets/robot.png';

const userStore = useUserStore();
const router = useRouter();

const logout = async () => {
  userStore.logout();
  router.push('/');
};
</script>

<template>
  <header class="header">
    <div class="header__left">
      <img :src="robotImage" alt="Logo" class="header__logo" />
      <h1 class="header__title">图灵 AI</h1>
    </div>

    <div class="header__right">
      <div class="header__user">
        <div class="header__avatar">
          {{ (userStore.name || 'U').charAt(0).toUpperCase() }}
        </div>
        <span class="header__username">{{ userStore.name || '用户' }}</span>
      </div>
      <button class="header__logout" @click="logout" title="退出登录">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
        </svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-6);
  background-color: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
  height: var(--header-height);
}

.header__left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.header__logo {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
}

.header__title {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.header__right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.header__user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.header__avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-light));
  color: white;
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  border-radius: var(--radius-full);
}

.header__username {
  font-size: var(--text-sm);
  color: var(--color-text);
}

.header__logout {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.header__logout:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-error);
}
</style>
