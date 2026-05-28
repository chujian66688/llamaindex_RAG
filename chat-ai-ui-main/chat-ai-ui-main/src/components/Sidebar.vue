<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../stores/user';
import { useChatStore } from '../stores/chat';
import { useSidebar } from '../composables/useSidebar';
import robotImage from '../assets/robot.png';

const router = useRouter();
const userStore = useUserStore();
const chatStore = useChatStore();
const { toggleSidebar } = useSidebar();
const searchQuery = ref('');
const deleteDialogVisible = ref(false);
const deleteTargetId = ref<string | null>(null);
const deleteTargetTitle = ref('');

// 过滤会话列表
const filteredConversations = computed(() => {
  if (!searchQuery.value) return chatStore.conversations;
  const query = searchQuery.value.toLowerCase();
  return chatStore.conversations.filter(c => 
    c.title.toLowerCase().includes(query)
  );
});

// 按日期分组
const groupedConversations = computed(() => {
  const groups: Map<string, typeof chatStore.conversations> = new Map();
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  for (const conv of filteredConversations.value) {
    const date = new Date(conv.updated_at);
    let group: string;
    
    if (date >= today) {
      group = '今天';
    } else if (date >= yesterday) {
      group = '昨天';
    } else if (date >= weekAgo) {
      group = '近7天';
    } else {
      group = '更早';
    }
    
    if (!groups.has(group)) {
      groups.set(group, []);
    }
    groups.get(group)!.push(conv);
  }
  
  return Array.from(groups.entries());
});

// 加载会话列表
onMounted(async () => {
  await chatStore.loadConversations();
});

const handleNewChat = () => {
  chatStore.currentConversationId = null;
  chatStore.messages = [];
  router.push('/chat');
};

const handleSelectConversation = async (id: string) => {
  await chatStore.switchConversation(id);
  router.push(`/chat/${id}`);
};

const handleDelete = (id: string) => {
  const conv = chatStore.conversations.find(c => c.id === id);
  deleteTargetId.value = id;
  deleteTargetTitle.value = conv?.title || '此会话';
  deleteDialogVisible.value = true;
};

const confirmDelete = async () => {
  if (deleteTargetId.value) {
    await chatStore.deleteConversation(deleteTargetId.value);
    // 如果删除的是当前会话，跳转到新对话
    if (chatStore.currentConversationId === null) {
      router.push('/chat');
    }
  }
  deleteDialogVisible.value = false;
  deleteTargetId.value = null;
};

const cancelDelete = () => {
  deleteDialogVisible.value = false;
  deleteTargetId.value = null;
};

const logout = async () => {
  chatStore.resetStore();
  userStore.logout();
  router.push('/');
};
</script>

<template>
  <div class="sidebar">
    <!-- 侧边栏头部 -->
    <div class="sidebar__header">
      <div class="sidebar__logo">
        <img :src="robotImage" alt="Logo" class="sidebar__logo-img" />
        <span class="sidebar__logo-text">图灵 AI</span>
      </div>
      <button class="sidebar__toggle" @click="toggleSidebar" title="收起侧边栏">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11 19l-7-7 7-7M18 19l-7-7 7-7" />
        </svg>
      </button>
    </div>

    <!-- 新建对话按钮 -->
    <button class="sidebar__new-chat" @click="handleNewChat">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 5v14M5 12h14" />
      </svg>
      <span>新建对话</span>
    </button>

    <!-- 搜索框 -->
    <div class="sidebar__search">
      <svg class="sidebar__search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" />
        <path d="M21 21l-4.35-4.35" />
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索对话..."
        class="sidebar__search-input"
      />
    </div>

    <!-- 对话列表 -->
    <div class="sidebar__conversations">
      <div v-for="[dateGroup, convs] in groupedConversations" :key="dateGroup" class="sidebar__group">
        <div class="sidebar__group-title">{{ dateGroup }}</div>
        <div
          v-for="conv in convs"
          :key="conv.id"
          class="sidebar__item"
          :class="{ 'sidebar__item--active': chatStore.currentConversationId === conv.id }"
          @click="handleSelectConversation(conv.id)"
        >
          <div class="sidebar__item-content">
            <div class="sidebar__item-title">{{ conv.title }}</div>
          </div>
          <button
            class="sidebar__item-delete"
            @click.stop="handleDelete(conv.id)"
            title="删除"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="groupedConversations.length === 0" class="sidebar__empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
        </svg>
        <p>暂无对话记录</p>
        <button class="sidebar__empty-btn" @click="handleNewChat">开始新对话</button>
      </div>
    </div>

    <!-- 侧边栏底部 -->
    <div class="sidebar__footer">
      <div class="sidebar__user">
        <div class="sidebar__avatar">
          {{ (userStore.name || 'U').charAt(0).toUpperCase() }}
        </div>
        <div class="sidebar__user-info">
          <div class="sidebar__user-name">{{ userStore.name || '用户' }}</div>
          <div class="sidebar__user-status">在线</div>
        </div>
      </div>
      <button class="sidebar__logout" @click="logout" title="退出登录">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
        </svg>
      </button>
    </div>

    <!-- 删除确认弹框 -->
    <Teleport to="body">
      <Transition name="dialog">
        <div v-if="deleteDialogVisible" class="delete-dialog-overlay" @click.self="cancelDelete">
          <div class="delete-dialog">
            <div class="delete-dialog__icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4M12 16h.01" />
              </svg>
            </div>
            <h3 class="delete-dialog__title">确认删除</h3>
            <p class="delete-dialog__message">
              确定要删除会话「{{ deleteTargetTitle }}」吗？<br/>
              删除后将无法恢复。
            </p>
            <div class="delete-dialog__actions">
              <button class="delete-dialog__btn delete-dialog__btn--cancel" @click="cancelDelete">
                取消
              </button>
              <button class="delete-dialog__btn delete-dialog__btn--confirm" @click="confirmDelete">
                确认删除
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--space-4);
  gap: var(--space-2);
}

.sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
  margin-bottom: var(--space-2);
}

.sidebar__logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.sidebar__logo-img {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
}

.sidebar__logo-text {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.sidebar__toggle {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.sidebar__toggle:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text);
}

.sidebar__new-chat {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-accent);
  color: white;
  border-radius: var(--radius-lg);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.sidebar__new-chat:hover {
  background-color: var(--color-accent-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.sidebar__admin-btn {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  border-radius: var(--radius-lg);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  transition: all var(--transition-fast);
  border: 1px solid var(--color-border);
}

.sidebar__admin-btn:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text);
  border-color: var(--color-border-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.sidebar__search {
  position: relative;
  margin: var(--space-2) 0;
}

.sidebar__search-icon {
  position: absolute;
  left: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
}

.sidebar__search-input {
  width: 100%;
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-10);
  background-color: var(--color-bg-secondary);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--color-text);
  transition: all var(--transition-fast);
  outline: none;
}

.sidebar__search-input::placeholder {
  color: var(--color-text-tertiary);
}

.sidebar__search-input:focus {
  background-color: var(--color-bg-elevated);
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-accent-subtle);
}

.sidebar__conversations {
  flex: 1;
  overflow-y: auto;
  margin: var(--space-2) 0;
}

.sidebar__group {
  margin-bottom: var(--space-4);
}

.sidebar__group-title {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: var(--space-2) var(--space-2);
  margin-bottom: var(--space-1);
}

.sidebar__item {
  display: flex;
  align-items: center;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: var(--space-1);
  position: relative;
}

.sidebar__item:hover {
  background-color: var(--color-bg-secondary);
}

.sidebar__item--active {
  background-color: var(--color-accent-subtle);
}

.sidebar__item--active:hover {
  background-color: var(--color-accent-subtle);
}

.sidebar__item-content {
  flex: 1;
  min-width: 0;
}

.sidebar__item-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar__item-preview {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: var(--space-1);
}

.sidebar__item-delete {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  opacity: 0;
  transition: all var(--transition-fast);
}

.sidebar__item:hover .sidebar__item-delete {
  opacity: 1;
}

.sidebar__item-delete:hover {
  background-color: var(--color-error);
  color: white;
}

.sidebar__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-4);
  text-align: center;
}

.sidebar__empty p {
  color: var(--color-text-tertiary);
  margin-top: var(--space-4);
  font-size: var(--text-sm);
}

.sidebar__empty-btn {
  margin-top: var(--space-4);
  padding: var(--space-2) var(--space-4);
  background-color: var(--color-accent);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.sidebar__empty-btn:hover {
  background-color: var(--color-accent-dark);
}

.sidebar__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) 0;
  border-top: 1px solid var(--color-border);
  margin-top: auto;
}

.sidebar__user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.sidebar__avatar {
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

.sidebar__user-info {
  display: flex;
  flex-direction: column;
}

.sidebar__user-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.sidebar__user-status {
  font-size: var(--text-xs);
  color: var(--color-success);
}

.sidebar__logout {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.sidebar__logout:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-error);
}

/* 删除确认弹框 */
.delete-dialog-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.delete-dialog {
  background-color: var(--color-bg-elevated);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  max-width: 400px;
  width: 90%;
  box-shadow: var(--shadow-xl);
  text-align: center;
}

.delete-dialog__icon {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-4);
  color: var(--color-warning);
}

.delete-dialog__title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.delete-dialog__message {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-6);
}

.delete-dialog__actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}

.delete-dialog__btn {
  padding: var(--space-2) var(--space-6);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  min-width: 100px;
}

.delete-dialog__btn--cancel {
  background-color: var(--color-bg-secondary);
  color: var(--color-text);
}

.delete-dialog__btn--cancel:hover {
  background-color: var(--color-bg-tertiary);
}

.delete-dialog__btn--confirm {
  background-color: var(--color-error);
  color: white;
}

.delete-dialog__btn--confirm:hover {
  background-color: #dc2626;
  transform: translateY(-1px);
}

/* 弹框动画 */
.dialog-enter-active {
  transition: all 0.3s ease-out;
}

.dialog-leave-active {
  transition: all 0.2s ease-in;
}

.dialog-enter-from {
  opacity: 0;
}

.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .delete-dialog {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.dialog-enter-active .delete-dialog {
  transition: all 0.3s ease-out;
}

.dialog-leave-active .delete-dialog {
  transition: all 0.2s ease-in;
}

.dialog-leave-to .delete-dialog {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}
</style>
