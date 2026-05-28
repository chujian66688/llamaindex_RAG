<script setup lang="ts">
import { onMounted, nextTick, ref, watch } from 'vue';
import { useUserStore } from '../stores/user';
import { useChatStore } from '../stores/chat';
import { useRouter, useRoute } from 'vue-router';
import { useSidebar } from '../composables/useSidebar';
import MainLayout from '../layouts/MainLayout.vue';
import ChatInput from '../components/ChatInput.vue';
import MessageBubble from '../components/MessageBubble.vue';
import TypingIndicator from '../components/TypingIndicator.vue';
import { marked } from 'marked';
import hljs from 'highlight.js';
import { markedHighlight } from 'marked-highlight';

const userStore = useUserStore();
const chatStore = useChatStore();
const router = useRouter();
const route = useRoute();
const { isExpanded, toggleSidebar } = useSidebar();

// --- 折叠状态管理 ---
const sourcesCollapsed = ref<{ [key: number]: boolean }>({});

// --- 人机交互相关状态 ---
const editingIndex = ref<number | null>(null);
const editContent = ref('');
const clarificationAnswer = ref('');

// 确保用户已登录
if (!userStore.userId) {
  router.push('/');
}

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

const toggleSources = (index: number) => {
  if (sourcesCollapsed.value[index] === undefined) {
    sourcesCollapsed.value[index] = false;
  } else {
    sourcesCollapsed.value[index] = !sourcesCollapsed.value[index];
  }
};

const isCollapsed = (index: number) => {
  return sourcesCollapsed.value[index] !== false;
};

const renderSourceContent = (text: string) => {
  if (!text) return '';
  try {
    return marked.parse(text);
  } catch (e) {
    console.error('Markdown parsing error:', e);
    return text;
  }
};

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
  });
};

// --- 人机交互操作 ---
const startEdit = (index: number) => {
  editingIndex.value = index;
  editContent.value = chatStore.messages[index].content;
};

const cancelEdit = () => {
  editingIndex.value = null;
  editContent.value = '';
};

const approveDraft = async () => {
  await chatStore.resumeWriting('approve');
  scrollToBottom();
};

const submitEdit = async () => {
  if (editingIndex.value !== null && editContent.value.trim()) {
    await chatStore.resumeWriting('edit', editContent.value);
    editingIndex.value = null;
    editContent.value = '';
    scrollToBottom();
  }
};

const rewriteDraft = async () => {
  await chatStore.resumeWriting('rewrite');
  scrollToBottom();
};

const submitClarification = async () => {
  if (clarificationAnswer.value.trim()) {
    await chatStore.submitClarification(clarificationAnswer.value);
    clarificationAnswer.value = '';
    scrollToBottom();
  }
};

// 初始化页面后进行加载历史消息
onMounted(async () => {
  // 加载会话列表
  await chatStore.loadConversations();
  
  // 根据路由参数加载对应会话
  const conversationId = route.params.conversationId as string | undefined;
  if (conversationId) {
    await chatStore.switchConversation(conversationId);
  } else if (chatStore.conversations.length > 0) {
    // 如果没有指定会话ID，但有历史会话，加载最新的
    await chatStore.switchConversation(chatStore.conversations[0].id);
    router.replace(`/chat/${chatStore.conversations[0].id}`);
  }
  
  scrollToBottom();
});

// 监听路由变化
watch(
  () => route.params.conversationId,
  async (newId) => {
    if (newId && typeof newId === 'string') {
      await chatStore.switchConversation(newId);
      scrollToBottom();
    }
  }
);

// 使用响应式监听器
watch(
  () => chatStore.messages,
  () => {
    scrollToBottom();
  },
  { deep: true }
);
</script>

<template>
  <MainLayout :show-sidebar="true">
    <div class="chat-view">
      <!-- 聊天头部 -->
      <header class="chat-view__header">
        <div class="chat-view__header-left">
          <button
            v-if="!isExpanded"
            class="chat-view__expand-btn"
            @click="toggleSidebar"
            title="展开侧边栏"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <h1 class="chat-view__title">
            {{ chatStore.currentConversationId 
              ? chatStore.conversations.find(c => c.id === chatStore.currentConversationId)?.title || '对话中' 
              : '新对话' 
            }}
          </h1>
        </div>
      </header>

      <!-- 聊天消息容器 -->
      <div id="chat-container" class="chat-view__messages">
        <!-- 空状态 -->
        <div v-if="chatStore.messages.length === 0" class="chat-view__empty">
          <div class="chat-view__empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
          </div>
          <h2 class="chat-view__empty-title">开始对话</h2>
          <p class="chat-view__empty-desc">向我提问任何问题，我会尽力为你解答</p>
          <div class="chat-view__empty-suggestions">
            <button class="chat-view__suggestion" @click="chatStore.sendMessage('帮我解释一下量子计算', false)">
              帮我解释一下量子计算
            </button>
            <button class="chat-view__suggestion" @click="chatStore.sendMessage('写一首关于春天的诗', false)">
              写一首关于春天的诗
            </button>
            <button class="chat-view__suggestion" @click="chatStore.sendMessage('如何提高编程效率？', false)">
              如何提高编程效率？
            </button>
          </div>
        </div>

        <!-- 聊天消息列表 -->
        <div v-else class="chat-view__list">
          <div
            v-for="(msg, index) in chatStore.messages"
            :key="index"
            class="chat-view__message-wrapper"
          >
            <MessageBubble
              :role="msg.role as 'human' | 'ai'"
              :content="msg.content"
              :is-reviewing="msg.isReviewing"
              :is-clarification="msg.isClarification"
              :is-writing="msg.isWriting"
              :current-step="msg.currentStep"
              :animation-delay="index * 50"
            >
              <!-- 澄清提问面板 -->
              <template v-if="msg.role === 'ai' && msg.isClarification" #clarification-panel>
                <div class="chat-view__clarification-panel">
                  <div class="chat-view__clarification-header">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>需要更多信息</span>
                  </div>
                  <div class="chat-view__clarification-input">
                    <textarea
                      v-model="clarificationAnswer"
                      class="chat-view__clarification-textarea"
                      placeholder="请补充说明您的写作需求..."
                      @keydown.enter.ctrl="submitClarification"
                    />
                    <div class="chat-view__clarification-actions">
                      <span class="chat-view__clarification-hint">Ctrl+Enter 发送</span>
                      <button class="chat-view__clarification-submit" @click="submitClarification" :disabled="!clarificationAnswer.trim()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                        </svg>
                        发送
                      </button>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 审阅面板 -->
              <template v-if="msg.role === 'ai' && msg.isReviewing" #review-panel>
                <div class="chat-view__review-panel">
                  <div class="chat-view__review-header">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>草稿已生成，请审阅</span>
                  </div>

                  <!-- 编辑模式 -->
                  <div v-if="editingIndex === index" class="chat-view__edit">
                    <textarea
                      v-model="editContent"
                      class="chat-view__edit-textarea"
                      placeholder="编辑草稿内容..."
                    />
                    <div class="chat-view__edit-actions">
                      <button class="chat-view__edit-btn chat-view__edit-btn--cancel" @click="cancelEdit">
                        取消
                      </button>
                      <button class="chat-view__edit-btn chat-view__edit-btn--submit" @click="submitEdit">
                        提交修改
                      </button>
                    </div>
                  </div>

                  <!-- 操作按钮 -->
                  <div v-else class="chat-view__review-actions">
                    <button class="chat-view__review-btn chat-view__review-btn--approve" @click="approveDraft">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M5 13l4 4L19 7" />
                      </svg>
                      确认通过
                    </button>
                    <button class="chat-view__review-btn chat-view__review-btn--edit" @click="startEdit(index)">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      修改内容
                    </button>
                    <button class="chat-view__review-btn chat-view__review-btn--rewrite" @click="rewriteDraft">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      重新生成
                    </button>
                  </div>
                </div>
              </template>
            </MessageBubble>

            <!-- 来源信息 -->
            <div
              v-if="msg.role === 'ai' && msg.sources && msg.sources.length > 0"
              class="chat-view__sources"
            >
              <button
                class="chat-view__sources-toggle"
                @click="toggleSources(index)"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>相关来源 ({{ msg.sources.length }})</span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  :class="{ 'rotated': !isCollapsed(index) }"
                >
                  <path d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              <Transition name="collapse">
                <div v-show="!isCollapsed(index)" class="chat-view__sources-content">
                  <div
                    v-for="(source, sourceIndex) in msg.sources"
                    :key="sourceIndex"
                    class="chat-view__source"
                  >
                    <div class="chat-view__source-header">
                      <span>来源 {{ sourceIndex + 1 }}</span>
                    </div>
                    <div
                      class="chat-view__source-body"
                      v-html="renderSourceContent(source)"
                    />
                  </div>
                </div>
              </Transition>
            </div>
          </div>

          <!-- 加载状态 -->
          <TypingIndicator
            v-if="chatStore.isLoading && !chatStore.isWaitingReview && !chatStore.isWaitingClarification"
            :message="chatStore.currentWritingStep || '正在思考中...'"
          />
        </div>
      </div>

      <!-- 输入框 -->
      <div class="chat-view__input">
        <ChatInput 
          :is-loading="chatStore.isLoading"
          :is-waiting-interaction="chatStore.isWaitingReview || chatStore.isWaitingClarification"
          @send="chatStore.sendMessage" 
          @pause="chatStore.pauseStream"
        />
      </div>
    </div>
  </MainLayout>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--color-bg);
}

/* 头部 */
.chat-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  background-color: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
  height: var(--header-height);
}

.chat-view__header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.chat-view__expand-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.chat-view__expand-btn:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.chat-view__title {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

/* 消息容器 */
.chat-view__messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
  scroll-behavior: smooth;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 空状态 */
.chat-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  animation: fadeInUp var(--transition-slow) ease-out;
}

.chat-view__empty-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-2xl);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-6);
  animation: float 3s ease-in-out infinite;
}

.chat-view__empty-title {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.chat-view__empty-desc {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-8);
}

.chat-view__empty-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  justify-content: center;
  max-width: 600px;
}

.chat-view__suggestion {
  padding: var(--space-3) var(--space-5);
  background-color: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  color: var(--color-text);
  transition: all var(--transition-fast);
}

.chat-view__suggestion:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

/* 消息列表 */
.chat-view__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.chat-view__message-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* 来源信息 */
.chat-view__sources {
  margin-left: 48px;
  max-width: 600px;
}

.chat-view__sources-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
  width: 100%;
}

.chat-view__sources-toggle:hover {
  background-color: var(--color-bg-tertiary);
}

.chat-view__sources-toggle svg:last-child {
  margin-left: auto;
  transition: transform var(--transition-base);
}

.chat-view__sources-toggle svg:last-child.rotated {
  transform: rotate(180deg);
}

.chat-view__sources-content {
  margin-top: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chat-view__source {
  background-color: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.chat-view__source-header {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
}

.chat-view__source-body {
  padding: var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
}

/* 折叠动画 */
.collapse-enter-active {
  transition: all var(--transition-base) ease-out;
}

.collapse-leave-active {
  transition: all var(--transition-fast) ease-in;
}

.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 审阅面板 */
.chat-view__review-panel {
  margin-top: var(--space-3);
  padding: var(--space-4);
  background-color: var(--color-bg-elevated);
  border: 2px solid var(--color-accent);
  border-radius: var(--radius-lg);
  box-shadow: 0 0 0 4px var(--color-accent-subtle);
}

/* 澄清提问面板 */
.chat-view__clarification-panel {
  margin-top: var(--space-3);
  padding: var(--space-4);
  background-color: var(--color-bg-elevated);
  border: 2px solid var(--color-warning);
  border-radius: var(--radius-lg);
  box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.1);
}

.chat-view__clarification-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-warning);
}

.chat-view__clarification-input {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chat-view__clarification-textarea {
  width: 100%;
  min-height: 100px;
  padding: var(--space-4);
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: inherit;
  font-size: var(--text-sm);
  color: var(--color-text);
  resize: vertical;
  outline: none;
  transition: border-color var(--transition-fast);
}

.chat-view__clarification-textarea:focus {
  border-color: var(--color-warning);
}

.chat-view__clarification-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-view__clarification-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.chat-view__clarification-submit {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background-color: var(--color-warning);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.chat-view__clarification-submit:hover:not(:disabled) {
  background-color: #d97706;
  transform: translateY(-1px);
}

.chat-view__clarification-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-view__review-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
}

.chat-view__edit {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chat-view__edit-textarea {
  width: 100%;
  min-height: 200px;
  padding: var(--space-4);
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: inherit;
  font-size: var(--text-sm);
  color: var(--color-text);
  resize: vertical;
  outline: none;
  transition: border-color var(--transition-fast);
}

.chat-view__edit-textarea:focus {
  border-color: var(--color-accent);
}

.chat-view__edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.chat-view__edit-btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.chat-view__edit-btn--cancel {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.chat-view__edit-btn--cancel:hover {
  background-color: var(--color-bg-tertiary);
}

.chat-view__edit-btn--submit {
  background-color: var(--color-accent);
  color: white;
}

.chat-view__edit-btn--submit:hover {
  background-color: var(--color-accent-dark);
}

.chat-view__review-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.chat-view__review-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.chat-view__review-btn--approve {
  background-color: var(--color-success);
  color: white;
}

.chat-view__review-btn--approve:hover {
  background-color: #16a34a;
  transform: translateY(-1px);
}

.chat-view__review-btn--edit {
  background-color: var(--color-warning);
  color: white;
}

.chat-view__review-btn--edit:hover {
  background-color: #d97706;
  transform: translateY(-1px);
}

.chat-view__review-btn--rewrite {
  background-color: var(--color-accent);
  color: white;
}

.chat-view__review-btn--rewrite:hover {
  background-color: var(--color-accent-dark);
  transform: translateY(-1px);
}

/* 输入框 */
.chat-view__input {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border);
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

/* 响应式 */
@media (max-width: 768px) {
  .chat-view__messages {
    padding: var(--space-4);
  }

  .chat-view__input {
    padding: var(--space-3) var(--space-4);
  }

  .chat-view__sources {
    margin-left: 0;
  }
}
</style>
