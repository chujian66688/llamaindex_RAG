import { ref, computed, onMounted, onUnmounted, watch, type Ref } from 'vue';
import { useRoute } from 'vue-router';

/**
 * 侧边栏状态类型
 */
export type SidebarView = 'conversations' | 'settings' | 'search';

/**
 * 对话项接口
 */
export interface ConversationItem {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: number;
  unreadCount?: number;
}

// 全局共享状态
const isExpanded = ref(true);
const currentView = ref<SidebarView>('conversations');
const searchQuery = ref('');
const conversations = ref<ConversationItem[]>([]);
const activeConversationId = ref<string | null>(null);
const isMobile = ref(false);

/**
 * 侧边栏状态管理 composable
 */
export function useSidebar() {
  const route = useRoute();
  
  // 过滤后的对话列表
  const filteredConversations = computed(() => {
    if (!searchQuery.value) {
      return conversations.value;
    }
    
    const query = searchQuery.value.toLowerCase();
    return conversations.value.filter(
      (conv) =>
        conv.title.toLowerCase().includes(query) ||
        conv.lastMessage.toLowerCase().includes(query)
    );
  });
  
  // 按日期分组的对话
  const groupedConversations = computed(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const lastWeek = new Date(today.getTime() - 7 * 86400000);
    
    const groups: Record<string, ConversationItem[]> = {
      '今天': [],
      '昨天': [],
      '过去 7 天': [],
      '更早': [],
    };
    
    filteredConversations.value.forEach((conv) => {
      const convDate = new Date(conv.timestamp);
      
      if (convDate >= today) {
        groups['今天'].push(conv);
      } else if (convDate >= yesterday) {
        groups['昨天'].push(conv);
      } else if (convDate >= lastWeek) {
        groups['过去 7 天'].push(conv);
      } else {
        groups['更早'].push(conv);
      }
    });
    
    // 过滤掉空分组
    return Object.entries(groups).filter(([_, items]) => items.length > 0);
  });
  
  // 切换侧边栏展开状态
  const toggleSidebar = () => {
    isExpanded.value = !isExpanded.value;
    
    // 持久化到 localStorage
    localStorage.setItem('sidebar-expanded', String(isExpanded.value));
  };
  
  // 切换视图
  const setView = (view: SidebarView) => {
    currentView.value = view;
  };
  
  // 选择对话
  const selectConversation = (id: string) => {
    activeConversationId.value = id;
  };
  
  // 新建对话
  const createNewConversation = () => {
    activeConversationId.value = null;
    // 这里可以触发路由导航到新对话
  };
  
  // 删除对话
  const deleteConversation = (id: string) => {
    conversations.value = conversations.value.filter((conv) => conv.id !== id);
    
    if (activeConversationId.value === id) {
      activeConversationId.value = null;
    }
  };
  
  // 清空搜索
  const clearSearch = () => {
    searchQuery.value = '';
  };
  
  const checkMobile = () => {
    isMobile.value = window.innerWidth < 768;
    
    // 移动端默认收起侧边栏
    if (isMobile.value) {
      isExpanded.value = false;
    }
  };
  
  // 监听路由变化，移动端自动收起侧边栏
  watch(
    () => route.path,
    () => {
      if (isMobile.value) {
        isExpanded.value = false;
      }
    }
  );
  
  onMounted(() => {
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    // 从 localStorage 恢复状态
    const savedExpanded = localStorage.getItem('sidebar-expanded');
    if (savedExpanded !== null && !isMobile.value) {
      isExpanded.value = savedExpanded === 'true';
    }
  });
  
  onUnmounted(() => {
    window.removeEventListener('resize', checkMobile);
  });
  
  return {
    // 状态
    isExpanded,
    currentView,
    searchQuery,
    conversations,
    activeConversationId,
    isMobile,
    
    // 计算属性
    filteredConversations,
    groupedConversations,
    
    // 方法
    toggleSidebar,
    setView,
    selectConversation,
    createNewConversation,
    deleteConversation,
    clearSearch,
  };
}

/**
 * 侧边栏宽度动画 composable
 */
export function useSidebarWidth(isExpanded: Ref<boolean>, collapsedWidth = 0, expandedWidth = 280) {
  const width = ref(isExpanded.value ? expandedWidth : collapsedWidth);
  const isAnimating = ref(false);
  
  watch(isExpanded, (newValue) => {
    isAnimating.value = true;
    width.value = newValue ? expandedWidth : collapsedWidth;
    
    // 动画结束后重置状态
    setTimeout(() => {
      isAnimating.value = false;
    }, 300);
  });
  
  const widthStyle = computed(() => ({
    width: `${width.value}px`,
    transition: isAnimating.value ? 'width 300ms cubic-bezier(0.4, 0, 0.2, 1)' : 'none',
  }));
  
  return {
    width,
    isAnimating,
    widthStyle,
  };
}
