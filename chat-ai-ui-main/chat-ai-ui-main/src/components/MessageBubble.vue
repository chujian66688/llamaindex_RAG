<script setup lang="ts">
import { computed } from 'vue';
import { marked } from 'marked';
import hljs from 'highlight.js';
import { markedHighlight } from 'marked-highlight';

interface Props {
  role: 'human' | 'ai';
  content: string;
  isReviewing?: boolean;
  isClarification?: boolean;
  isWriting?: boolean;
  currentStep?: string;
  animationDelay?: number;
}

const props = withDefaults(defineProps<Props>(), {
  isReviewing: false,
  isClarification: false,
  isWriting: false,
  currentStep: '',
  animationDelay: 0,
});

// 配置 marked
marked.use(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang }).value;
        } catch (err) {}
      }
      return hljs.highlightAuto(code).value;
    },
  })
);

const isHuman = computed(() => props.role === 'human');

const formattedContent = computed(() => {
  if (!props.content) return '';
  
  if (isHuman.value) {
    return props.content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>');
  }
  
  return marked(props.content);
});

const animationStyle = computed(() => ({
  animationDelay: `${props.animationDelay}ms`,
}));
</script>

<template>
  <div
    class="message-bubble"
    :class="[
      `message-bubble--${role}`,
      { 'message-bubble--reviewing': isReviewing },
      { 'message-bubble--clarification': isClarification },
      { 'message-bubble--writing': isWriting },
      { 'message-bubble--empty': !content && !isReviewing && !isClarification && !isHuman },
    ]"
    :style="animationStyle"
    v-if="content || isReviewing || isClarification || isHuman"
  >
    <!-- 头像 -->
    <div class="message-bubble__avatar" v-if="content || isReviewing || isClarification || isHuman">
      <template v-if="isHuman">
        <div class="message-bubble__avatar-human">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      </template>
      <template v-else>
        <div class="message-bubble__avatar-ai">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a2 2 0 012 2v2a2 2 0 01-2 2h-1.27A7 7 0 0114 22h-4a7 7 0 01-6.73-4H2a2 2 0 01-2-2v-2a2 2 0 012-2h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" />
            <circle cx="8.5" cy="14.5" r="1.5" />
            <circle cx="15.5" cy="14.5" r="1.5" />
          </svg>
        </div>
      </template>
    </div>

    <!-- 消息内容 -->
    <div class="message-bubble__content">
      <!-- 写作状态提示 -->
      <div v-if="isWriting && currentStep" class="message-bubble__step">
        <div class="message-bubble__step-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span>{{ currentStep }}</span>
      </div>

      <!-- 消息气泡 -->
      <div
        v-if="content || isReviewing || isClarification"
        class="message-bubble__bubble"
        v-html="formattedContent"
      />

      <!-- 澄清提问面板 -->
      <slot name="clarification-panel" />

      <!-- 审阅状态面板 -->
      <slot name="review-panel" />
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  display: flex;
  gap: var(--space-3);
  max-width: 100%;
  animation: fadeInUp var(--transition-slow) ease-out backwards;
}

.message-bubble--human {
  flex-direction: row-reverse;
}

.message-bubble__avatar {
  flex-shrink: 0;
}

.message-bubble__avatar-human,
.message-bubble__avatar-ai {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  transition: transform var(--transition-fast);
}

.message-bubble:hover .message-bubble__avatar-human,
.message-bubble:hover .message-bubble__avatar-ai {
  transform: scale(1.05);
}

.message-bubble__avatar-human {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.message-bubble__avatar-ai {
  background: linear-gradient(135deg, #f093fb, #f5576c);
  color: white;
  animation: float 3s ease-in-out infinite;
}

.message-bubble__content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.message-bubble--human .message-bubble__content {
  align-items: flex-end;
}

.message-bubble__step {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  animation: fadeIn var(--transition-base) ease-out;
}

.message-bubble__step-indicator {
  display: flex;
  gap: 3px;
}

.message-bubble__step-indicator span {
  width: 4px;
  height: 4px;
  background-color: var(--color-accent);
  border-radius: var(--radius-full);
  animation: bounce 1.4s ease-in-out infinite;
}

.message-bubble__step-indicator span:nth-child(1) {
  animation-delay: 0s;
}

.message-bubble__step-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.message-bubble__step-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

.message-bubble__bubble {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  line-height: 1.7;
  animation: scaleIn var(--transition-base) ease-out;
}

.message-bubble--human .message-bubble__bubble {
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-dark));
  color: white;
  border-bottom-right-radius: var(--radius-sm);
  max-width: 80%;
}

.message-bubble--ai .message-bubble__bubble {
  background-color: var(--color-bg-elevated);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.message-bubble--reviewing .message-bubble__bubble {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-subtle);
}

.message-bubble--clarification .message-bubble__bubble {
  border-color: var(--color-warning);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

/* 消息内容样式 */
.message-bubble__bubble :deep(p) {
  margin-bottom: 0.75em;
}

.message-bubble__bubble :deep(p:last-child) {
  margin-bottom: 0;
}

.message-bubble__bubble :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.9em;
  padding: 0.2em 0.4em;
  background-color: rgba(0, 0, 0, 0.06);
  border-radius: var(--radius-sm);
}

.message-bubble--human .message-bubble__bubble :deep(code) {
  background-color: rgba(255, 255, 255, 0.2);
}

.message-bubble__bubble :deep(pre) {
  margin: 0.75em 0;
  padding: 1em;
  background-color: var(--color-primary);
  border-radius: var(--radius-md);
  overflow-x: auto;
}

.message-bubble__bubble :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: var(--color-text-inverse);
}

.message-bubble__bubble :deep(ul),
.message-bubble__bubble :deep(ol) {
  margin-left: 1.5em;
  margin-bottom: 0.75em;
}

.message-bubble__bubble :deep(li) {
  margin-bottom: 0.5em;
}

.message-bubble__bubble :deep(blockquote) {
  border-left: 3px solid var(--color-accent);
  padding-left: 1em;
  margin: 0.75em 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.message-bubble__bubble :deep(strong) {
  font-weight: var(--font-semibold);
}

.message-bubble__bubble :deep(a) {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.message-bubble__bubble :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-md);
  margin: 0.75em 0;
}

.message-bubble__bubble :deep(h1) {
  font-size: 1.5em;
  font-weight: 700;
  margin-bottom: 0.5em;
  margin-top: 1em;
}

.message-bubble__bubble :deep(h1:first-child) {
  margin-top: 0;
}

.message-bubble__bubble :deep(h2) {
  font-size: 1.25em;
  font-weight: 600;
  margin-bottom: 0.5em;
  margin-top: 1em;
}

.message-bubble__bubble :deep(h2:first-child) {
  margin-top: 0;
}

.message-bubble__bubble :deep(h3) {
  font-size: 1.1em;
  font-weight: 600;
  margin-bottom: 0.5em;
  margin-top: 1em;
}

.message-bubble__bubble :deep(h3:first-child) {
  margin-top: 0;
}

/* 悬停效果 */
.message-bubble:hover .message-bubble__bubble {
  box-shadow: var(--shadow-md);
}
</style>
