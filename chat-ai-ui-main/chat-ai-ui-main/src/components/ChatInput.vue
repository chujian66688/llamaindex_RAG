<script setup lang="ts">
import { ref, computed } from 'vue';

interface Props {
  isLoading?: boolean;
  isWaitingInteraction?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  isWaitingInteraction: false,
});

const message = ref('');
const isFocused = ref(false);
const useKnowledge = ref(false);  // 知识库开关，默认关闭
const emit = defineEmits(['send', 'pause']);

const hasContent = computed(() => message.value.trim().length > 0);
const isDisabled = computed(() => props.isLoading || props.isWaitingInteraction);

const sendMessage = () => {
  if (!message.value.trim() || isDisabled.value) return;
  emit('send', message.value, useKnowledge.value);
  message.value = '';
};

const toggleKnowledge = () => {
  useKnowledge.value = !useKnowledge.value;
};

const pauseGeneration = () => {
  emit('pause');
};
</script>

<template>
  <div class="chat-input" :class="{ 'chat-input--focused': isFocused }">
    <div class="chat-input__wrapper">
      <!-- 知识库开关按钮 -->
      <button
        class="chat-input__knowledge"
        :class="{
          'chat-input__knowledge--active': useKnowledge,
          'chat-input__knowledge--disabled': isDisabled
        }"
        @click="toggleKnowledge"
        :disabled="isDisabled"
        :title="useKnowledge ? '知识库已开启，点击关闭' : '知识库已关闭，点击开启'"
      >
        <svg v-if="useKnowledge" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
          <path d="M8 7h8M8 11h6" />
        </svg>
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
          <line x1="2" y1="2" x2="22" y2="22" />
        </svg>
        <!-- <span class="chat-input__knowledge-text">知识库</span> -->
      </button>

      <!-- 输入框 -->
      <div class="chat-input__field-wrapper">
        <input
          v-model="message"
          @keyup.enter="sendMessage"
          @focus="isFocused = true"
          @blur="isFocused = false"
          :placeholder="isWaitingInteraction ? '请先完成上方的交互操作...' : (isLoading ? 'AI 正在回复中...' : '输入你的问题，开始 AI 对话...')"
          type="text"
          class="chat-input__field"
          :disabled="isDisabled"
        />
        <div class="chat-input__indicator" v-if="message.length > 0 && !isDisabled">
          <span class="chat-input__char-count">{{ message.length }}</span>
        </div>
      </div>

      <!-- 发送/暂停按钮 -->
      <button
        v-if="!isLoading"
        @click="sendMessage"
        :disabled="!hasContent || isWaitingInteraction"
        class="chat-input__send"
        :class="{ 'chat-input__send--active': hasContent && !isWaitingInteraction }"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
        </svg>
      </button>

      <!-- 暂停按钮 -->
      <button
        v-else
        @click="pauseGeneration"
        class="chat-input__pause"
        title="停止生成"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>
    </div>

    <!-- 提示文字 -->
    <div class="chat-input__hints">
      <template v-if="isWaitingInteraction">
        <span class="chat-input__hint chat-input__hint--warning">
          请先完成上方的交互操作
        </span>
      </template>
      <template v-else-if="!isLoading">
        <span class="chat-input__hint">
          按 <kbd>Enter</kbd> 发送
        </span>
        <span class="chat-input__hint">
          <kbd>Shift</kbd> + <kbd>Enter</kbd> 换行
        </span>
      </template>
      <template v-else>
        <span class="chat-input__hint chat-input__hint--loading">
          AI 正在生成回复，点击停止按钮可中断
        </span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.chat-input {
  padding: var(--space-4);
  background-color: var(--color-bg-elevated);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.chat-input--focused {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-subtle), var(--shadow-md);
}

.chat-input__wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 知识库开关按钮 */
.chat-input__knowledge {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  flex-shrink: 0;
  background-color: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-border);
}

.chat-input__knowledge:hover:not(:disabled) {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border-color: var(--color-border-hover);
}

.chat-input__knowledge--active {
  background-color: var(--color-accent-subtle);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.chat-input__knowledge--active:hover:not(:disabled) {
  background-color: var(--color-accent);
  color: white;
}

.chat-input__knowledge--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-input__knowledge-text {
  font-size: var(--text-xs);
}

/* 输入框 */
.chat-input__field-wrapper {
  flex: 1;
  position: relative;
  min-width: 0;
}

.chat-input__field {
  width: 100%;
  padding: var(--space-3);
  background: transparent;
  border: none;
  font-size: var(--text-base);
  color: var(--color-text);
  outline: none;
  box-sizing: border-box;
}

.chat-input__field:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.chat-input__field::placeholder {
  color: var(--color-text-tertiary);
}

.chat-input__indicator {
  position: absolute;
  right: 0;
  bottom: -4px;
}

.chat-input__char-count {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 发送按钮 */
.chat-input__send {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.chat-input__send--active {
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-dark));
  color: white;
  box-shadow: 0 4px 12px rgba(74, 108, 247, 0.3);
}

.chat-input__send--active:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(74, 108, 247, 0.4);
}

.chat-input__send:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

/* 暂停按钮 */
.chat-input__pause {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  flex-shrink: 0;
  animation: pulse-border 2s ease-in-out infinite;
}

.chat-input__pause:hover {
  background-color: var(--color-error);
  color: white;
  border-color: var(--color-error);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

@keyframes pulse-border {
  0%, 100% {
    border-color: var(--color-border);
  }
  50% {
    border-color: var(--color-error);
  }
}

/* 提示文字 */
.chat-input__hints {
  display: flex;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-2);
}

.chat-input__hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.chat-input__hint--loading {
  color: var(--color-warning);
  animation: fade-pulse 1.5s ease-in-out infinite;
}

.chat-input__hint--warning {
  color: var(--color-warning);
  font-weight: var(--font-medium);
}

@keyframes fade-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.chat-input__hint kbd {
  display: inline-block;
  padding: 2px 6px;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 11px;
  border: 1px solid var(--color-border);
}
</style>
