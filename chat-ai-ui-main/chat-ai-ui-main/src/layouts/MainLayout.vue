<script setup lang="ts">
import { computed } from 'vue';
import { useSidebar } from '../composables/useSidebar';
import Sidebar from '../components/Sidebar.vue';

interface Props {
  showSidebar?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showSidebar: true,
});

const { isExpanded, isMobile } = useSidebar();

const contentStyle = computed(() => {
  const left = props.showSidebar && isExpanded.value ? 'var(--sidebar-width)' : '0';
  return {
    marginLeft: left,
  };
});
</script>

<template>
  <div class="main-layout">
    <!-- 左侧边栏 -->
    <Transition name="slide-sidebar">
      <aside
        v-if="showSidebar && isExpanded"
        class="main-layout__sidebar"
      >
        <Sidebar />
      </aside>
    </Transition>

    <!-- 主内容区 -->
    <main class="main-layout__content" :style="contentStyle">
      <slot />
    </main>

    <!-- 移动端遮罩 -->
    <Transition name="fade">
      <div
        v-if="isMobile && isExpanded"
        class="main-layout__overlay"
        @click="isExpanded = false"
      />
    </Transition>
  </div>
</template>

<style scoped>
.main-layout {
  display: flex;
  min-height: 100vh;
  background-color: var(--color-bg);
  position: relative;
}

.main-layout__sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 40;
  background-color: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}

.main-layout__sidebar--expanded {
  width: var(--sidebar-width);
}

.main-layout__content {
  flex: 1;
  height: 100vh;
  transition: margin var(--transition-slow);
  overflow: hidden;
}

.main-layout__overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 35;
  backdrop-filter: blur(4px);
}

/* 侧边栏滑入动画 */
.slide-sidebar-enter-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-sidebar-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-sidebar-enter-from {
  transform: translateX(-100%);
}

.slide-sidebar-leave-to {
  transform: translateX(-100%);
}

/* 淡入淡出动画 */
.fade-enter-active {
  transition: opacity var(--transition-base) ease-out;
}

.fade-leave-active {
  transition: opacity var(--transition-fast) ease-in;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 移动端响应式 */
@media (max-width: 768px) {
  .main-layout__sidebar {
    width: 280px;
  }

  .main-layout__content {
    margin-left: 0 !important;
  }
}
</style>
