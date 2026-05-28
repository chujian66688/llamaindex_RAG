<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useUserStore } from '../stores/user';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

const sidebarItems = [
  {
    label: '文档管理',
    icon: 'docs',
    path: '/admin/documents',
  },
  {
    label: '用户管理',
    icon: 'users',
    path: '/admin/users',
  },
];

const activePath = computed(() => route.path);

function handleNav(path: string) {
  router.push(path);
}
</script>

<template>
  <div class="admin-layout">
    <!-- 左侧导航 -->
    <aside class="admin-sidebar">
      <div class="admin-sidebar__header">
        <h1 class="admin-sidebar__title">后台管理</h1>
      </div>

      <nav class="admin-sidebar__nav">
        <button
          v-for="item in sidebarItems"
          :key="item.path"
          class="admin-sidebar__item"
          :class="{ 'admin-sidebar__item--active': activePath === item.path }"
          @click="handleNav(item.path)"
        >
          <svg v-if="item.icon === 'docs'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14,2 14,8 20,8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <svg v-else-if="item.icon === 'users'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
          </svg>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="admin-sidebar__footer">
        <div class="admin-sidebar__user">
          <div class="admin-sidebar__avatar">
            {{ (userStore.name || 'A').charAt(0).toUpperCase() }}
          </div>
          <div class="admin-sidebar__user-info">
            <div class="admin-sidebar__user-name">{{ userStore.name || '管理员' }}</div>
            <div class="admin-sidebar__user-role">管理员</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="admin-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  background-color: var(--color-bg);
}

.admin-sidebar {
  width: 240px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border);
  flex-shrink: 0;
}

.admin-sidebar__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.admin-sidebar__title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.admin-sidebar__nav {
  flex: 1;
  padding: var(--space-4) var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.admin-sidebar__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.admin-sidebar__item:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.admin-sidebar__item--active {
  background-color: var(--color-accent-subtle);
  color: var(--color-accent);
}

.admin-sidebar__item--active:hover {
  background-color: var(--color-accent-subtle);
}

.admin-sidebar__footer {
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.admin-sidebar__user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.admin-sidebar__avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-light));
  color: white;
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  border-radius: var(--radius-full);
}

.admin-sidebar__user-info {
  display: flex;
  flex-direction: column;
}

.admin-sidebar__user-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.admin-sidebar__user-role {
  font-size: var(--text-xs);
  color: var(--color-accent);
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

/* 响应式 */
@media (max-width: 768px) {
  .admin-sidebar {
    width: 60px;
  }

  .admin-sidebar__title,
  .admin-sidebar__item span,
  .admin-sidebar__user-info {
    display: none;
  }

  .admin-sidebar__item {
    justify-content: center;
    padding: var(--space-3);
  }

  .admin-sidebar__header {
    justify-content: center;
  }

  .admin-sidebar__user {
    justify-content: center;
  }
}
</style>
