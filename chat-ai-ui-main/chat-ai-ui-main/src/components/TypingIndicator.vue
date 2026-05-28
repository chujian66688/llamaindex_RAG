<script setup lang="ts">
interface Props {
  message?: string;
}

withDefaults(defineProps<Props>(), {
  message: '正在思考中...',
});
</script>

<template>
  <div class="typing-indicator">
    <div class="typing-indicator__avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a2 2 0 012 2v2a2 2 0 01-2 2h-1.27A7 7 0 0114 22h-4a7 7 0 01-6.73-4H2a2 2 0 01-2-2v-2a2 2 0 012-2h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" />
        <circle cx="8.5" cy="14.5" r="1.5" />
        <circle cx="15.5" cy="14.5" r="1.5" />
      </svg>
    </div>
    <div class="typing-indicator__content">
      <div class="typing-indicator__bubble">
        <div class="typing-indicator__dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span class="typing-indicator__text">{{ message }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.typing-indicator {
  display: flex;
  gap: var(--space-3);
  animation: fadeInUp var(--transition-slow) ease-out;
}

.typing-indicator__avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f093fb, #f5576c);
  color: white;
  border-radius: var(--radius-full);
  animation: float 3s ease-in-out infinite;
}

.typing-indicator__content {
  flex: 1;
}

.typing-indicator__bubble {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  border-bottom-left-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.typing-indicator__dots {
  display: flex;
  gap: 4px;
}

.typing-indicator__dots span {
  width: 6px;
  height: 6px;
  background-color: var(--color-accent);
  border-radius: var(--radius-full);
  animation: bounce 1.4s ease-in-out infinite;
}

.typing-indicator__dots span:nth-child(1) {
  animation-delay: 0s;
}

.typing-indicator__dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator__dots span:nth-child(3) {
  animation-delay: 0.4s;
}

.typing-indicator__text {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}
</style>
