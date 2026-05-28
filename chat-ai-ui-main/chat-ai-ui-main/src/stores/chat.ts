import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';
import { useUserStore } from './user';

interface ChatMessage {
  role: string;
  content: string;
  sources: any[];
  isReviewing?: boolean;  // 是否处于人机交互状态（草稿审阅）
  isClarification?: boolean;  // 是否处于澄清提问状态
  clarificationQuestion?: string;  // 澄清问题内容
  draft?: string;  // 待审核的草稿内容
  currentStep?: string;  // 当前写作步骤（如"正在生成大纲..."）
  isWriting?: boolean;  // 是否处于写作流程中
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

/**
 * 带认证的 fetch 封装，自动处理 token 刷新
 * @param url - 请求 URL
 * @param options - fetch 选项
 * @returns Response 对象
 */
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const userStore = useUserStore();

  // 第一次请求
  const headers = new Headers(options.headers);
  if (userStore.token) {
    headers.set('Authorization', `Bearer ${userStore.token}`);
  }

  let response = await fetch(url, { ...options, headers });

  // 如果是 401，尝试刷新 token
  if (response.status === 401 && userStore.refreshToken) {
    const refreshed = await userStore.refreshAccessToken();
    if (refreshed) {
      // 刷新成功，重试请求
      headers.set('Authorization', `Bearer ${userStore.token}`);
      response = await fetch(url, { ...options, headers });
    } else {
      // 刷新失败，跳转登录页
      window.location.href = '/';
      throw new Error('Token refresh failed');
    }
  } else if (response.status === 401) {
    // 没有 refresh_token，直接登出
    userStore.logout();
    window.location.href = '/';
    throw new Error('Unauthorized');
  }

  return response;
}


export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([]);
  const isLoading = ref(false);
  const isWaitingReview = ref(false);  // 是否正在等待用户审阅
  const isWaitingClarification = ref(false);  // 是否正在等待用户澄清
  const currentWritingStep = ref('');  // 当前写作步骤描述
  const isPaused = ref(false);  // 是否处于暂停状态

  // 会话相关状态
  const conversations = ref<Conversation[]>([]);
  const currentConversationId = ref<string | null>(null);

  // 文章撰写相关状态
  const articleContent = ref('');  // 文章内容
  const isArticleWriting = ref(false);  // 是否正在撰写文章
  const currentNode = ref('');  // 当前执行的节点名称

  const userStore = useUserStore();

  // 用于中止 fetch 请求
  let abortController: AbortController | null = null;

  // ===== 会话管理方法 =====

  /**
   * 加载会话列表
   */
  const loadConversations = async () => {
    if (!userStore.token) return;
    try {
      const { data } = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/chat/conversations`,
        { headers: { 'Authorization': `Bearer ${userStore.token}` } }
      );
      conversations.value = data.conversations || [];
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  /**
   * 创建新会话
   */
  const createConversation = async (title?: string): Promise<string | null> => {
    if (!userStore.token) return null;
    try {
      const { data } = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/chat/conversations`,
        { title: title || '新对话' },
        { headers: { 'Authorization': `Bearer ${userStore.token}` } }
      );
      const newConversation: Conversation = {
        id: data.id,
        title: data.title,
        created_at: data.created_at,
        updated_at: data.updated_at,
      };
      conversations.value.unshift(newConversation);
      currentConversationId.value = newConversation.id;
      messages.value = [];
      return newConversation.id;
    } catch (error) {
      console.error('Error creating conversation:', error);
      return null;
    }
  };

  /**
   * 切换会话
   */
  const switchConversation = async (conversationId: string) => {
    if (currentConversationId.value === conversationId) return;
    currentConversationId.value = conversationId;
    messages.value = [];
    await loadChatHistory();
  };

  /**
   * 删除会话
   */
  const deleteConversation = async (conversationId: string) => {
    if (!userStore.token) return;
    try {
      await axios.delete(
        `${import.meta.env.VITE_API_URL}/api/chat/conversations/${conversationId}`,
        { headers: { 'Authorization': `Bearer ${userStore.token}` } }
      );
      conversations.value = conversations.value.filter(c => c.id !== conversationId);
      // 如果删除的是当前会话，切换到第一个会话或清空
      if (currentConversationId.value === conversationId) {
        if (conversations.value.length > 0) {
          await switchConversation(conversations.value[0].id);
        } else {
          currentConversationId.value = null;
          messages.value = [];
        }
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  /**
   * 重命名会话
   */
  const renameConversation = async (conversationId: string, title: string) => {
    if (!userStore.token) return;
    try {
      const { data } = await axios.patch(
        `${import.meta.env.VITE_API_URL}/api/chat/conversations/${conversationId}`,
        { title },
        { headers: { 'Authorization': `Bearer ${userStore.token}` } }
      );
      const index = conversations.value.findIndex(c => c.id === conversationId);
      if (index !== -1) {
        conversations.value[index].title = data.title;
      }
    } catch (error) {
      console.error('Error renaming conversation:', error);
    }
  };

  // ===== 聊天方法 =====

  /**
   * 获取历史消息接口调用
   */
  const loadChatHistory = async () => {
    if (!userStore.token || !currentConversationId.value) return;

    try {
      const { data } = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/chat/history`,
        {
          params: { conversation_id: currentConversationId.value },
          headers: { 'Authorization': `Bearer ${userStore.token}` }
        }
      );
      messages.value = data.filter((msg: ChatMessage) => msg);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  /**
   * 对话接口调用
   */
  const sendMessage = async (message: string, knowledge_bool: boolean) => {
    if (!message.trim() || !userStore.token) return;

    // 如果没有当前会话，先创建一个
    if (!currentConversationId.value) {
      const title = message.substring(0, 20) + (message.length > 20 ? '...' : '');
      const newId = await createConversation(title);
      if (!newId) {
        console.error('Failed to create conversation');
        return;
      }
    }

    // 重置所有消息的写作状态
    messages.value.forEach(msg => {
      if (msg.isWriting) {
        msg.isWriting = false;
        msg.currentStep = '';
      }
    });

    messages.value.push({ role: 'human', content: message, sources: [] });

    isLoading.value = true;
    isPaused.value = false;

    try {
      await handleStreamResponse(message, knowledge_bool);
    } catch (error) {
      console.error('Error sending message: ', error);
      messages.value.push({
        role: 'ai',
        content: 'Error: unable to process request',
        sources: []
      });
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * 处理流式响应
   */
  const handleStreamResponse = async (message: string, knowledge_bool: boolean) => {
    const aiMessageIndex = messages.value.length;
    messages.value.push({ role: 'ai', content: '', sources: [], isReviewing: false, draft: '' });
    
    // 创建新的 AbortController
    abortController = new AbortController();
    
    try {
      const response = await fetchWithAuth(`${import.meta.env.VITE_API_URL}/api/chat/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: message,
          conversation_id: currentConversationId.value,
          knowledge_bool: knowledge_bool,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let receivedFirstContent = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            const jsonStr = trimmedLine.slice(6);
            if (jsonStr.trim() === '' || jsonStr.trim() === '[DONE]') continue;

            try {
              const data = JSON.parse(jsonStr);
              if (data.finished) {
                break;
              }
              if (data.type === "conversation_id") {
                // 更新会话 ID
                if (data.content) {
                  currentConversationId.value = data.content;
                  // 刷新会话列表
                  loadConversations();
                }
              } else if (data.type === "sources") {
                if (data.content && Array.isArray(data.content)) {
                  messages.value[aiMessageIndex].sources = data.content;
                }
              } else if (data.type === "node_start") {
                // 中间步骤开始，更新状态
                currentNode.value = data.node || '';
                
                // 如果进入 draft 节点，开始文章撰写模式
                if (data.node === 'draft') {
                  isArticleWriting.value = true;
                  articleContent.value = '';  // 清空之前的文章内容
                }
                
                if (!data.is_display) {
                  // 非显示节点，显示加载状态
                  messages.value[aiMessageIndex].currentStep = data.label || '';
                  messages.value[aiMessageIndex].isWriting = true;
                  currentWritingStep.value = data.label || '';
                } else {
                  // 显示节点开始，清除中间步骤状态
                  messages.value[aiMessageIndex].currentStep = '';
                  messages.value[aiMessageIndex].isWriting = false;
                  currentWritingStep.value = '';
                }
              } else if (data.type === "article") {
                // 文章内容事件（draft 节点的内容）
                if (data.content) {
                  articleContent.value += data.content;
                }
              } else if (data.type === "interrupt") {
                // 收到 interrupt 事件，进入人机交互模式
                const interruptData = data.content;
                const interruptValue = Array.isArray(interruptData) && interruptData[0]?.value
                  ? interruptData[0].value
                  : {};
                const interruptType = interruptValue.type || 'human_review';

                if (interruptType === 'clarification') {
                  // 澄清提问类型
                  const question = interruptValue.question || interruptValue.message || '请补充说明您的需求';
                  messages.value[aiMessageIndex].content = question;
                  messages.value[aiMessageIndex].isClarification = true;
                  messages.value[aiMessageIndex].clarificationQuestion = question;
                  messages.value[aiMessageIndex].currentStep = '';
                  messages.value[aiMessageIndex].isWriting = false;
                  isWaitingClarification.value = true;
                } else {
                  // 草稿审阅类型
                  const draft = interruptValue.draft || '';
                  messages.value[aiMessageIndex].content = draft;
                  messages.value[aiMessageIndex].isReviewing = true;
                  messages.value[aiMessageIndex].draft = draft;
                  isWaitingReview.value = true;
                }
                isLoading.value = false;
                currentWritingStep.value = '';
                
                // 文章撰写完成，保留文章内容供用户审阅
                isArticleWriting.value = false;
                
                reader.releaseLock();
                return;
              } else if (data.type === "content" || data.type === "text") {
                // 只显示 is_display 节点的内容
                if (data.content && data.is_display) {
                  if (!receivedFirstContent) {
                    receivedFirstContent = true;
                    isLoading.value = false;
                  }
                  messages.value[aiMessageIndex].content += data.content;
                }
              }
            } catch (e) {
              console.warn('Failed to parse JSON:', jsonStr, e);
            }
          }
        }
      }
      reader.releaseLock();

    } catch (error: any) {
      // 如果是用户主动暂停，不删除消息
      if (error.name === 'AbortError') {
        console.log('流式响应已暂停');
        // 保留已生成的内容，只清除加载状态
        if (messages.value[aiMessageIndex]) {
          messages.value[aiMessageIndex].isWriting = false;
          messages.value[aiMessageIndex].currentStep = '';
        }
        return;
      }
      console.error('Stream error:', error);
      messages.value.splice(aiMessageIndex, 1);
      throw error;
    } finally {
      abortController = null;
    }
  };

  /**
   * 恢复被 interrupt 暂停的写作流程
   * @param action - 用户操作：approve / edit / rewrite
   * @param content - 用户编辑后的内容（仅 action=edit 时需要）
   */
  const resumeWriting = async (action: string, content?: string) => {
    if (!userStore.token || !currentConversationId.value) return;

    isLoading.value = true;
    isWaitingReview.value = false;

    // 重置所有消息的写作状态
    messages.value.forEach(msg => {
      if (msg.isWriting) {
        msg.isWriting = false;
        msg.currentStep = '';
      }
    });

    // 找到当前正在审阅的消息并更新状态
    const reviewingIndex = messages.value.findIndex(m => m.isReviewing);
    if (reviewingIndex !== -1) {
      if (action === 'edit' && content) {
        messages.value[reviewingIndex].content = content;
      }
      messages.value[reviewingIndex].isReviewing = false;
    }

    // 添加用户操作消息
    if (action === 'approve') {
      messages.value.push({ role: 'human', content: '确认通过', sources: [] });
    } else if (action === 'edit') {
      messages.value.push({ role: 'human', content: '已修改内容', sources: [] });
    } else if (action === 'rewrite') {
      messages.value.push({ role: 'human', content: '重新生成', sources: [] });
    }

    const aiMessageIndex = messages.value.length;
    messages.value.push({ role: 'ai', content: '', sources: [], isReviewing: false, draft: '' });

    try {
      // 创建新的 AbortController
      abortController = new AbortController();

      // 使用流式接口恢复执行
      const response = await fetchWithAuth(`${import.meta.env.VITE_API_URL}/api/chat/chat/resume/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          conversation_id: currentConversationId.value,
          action, 
          content 
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let receivedFirstContent = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            const jsonStr = trimmedLine.slice(6);
            if (jsonStr.trim() === '' || jsonStr.trim() === '[DONE]') continue;

            try {
              const data = JSON.parse(jsonStr);
              if (data.finished) {
                break;
              }
              if (data.type === "sources") {
                if (data.content && Array.isArray(data.content)) {
                  messages.value[aiMessageIndex].sources = data.content;
                }
              } else if (data.type === "node_start") {
                // 中间步骤开始，更新状态
                if (!data.is_display) {
                  messages.value[aiMessageIndex].currentStep = data.label || '';
                  messages.value[aiMessageIndex].isWriting = true;
                  currentWritingStep.value = data.label || '';
                } else {
                  messages.value[aiMessageIndex].currentStep = '';
                  messages.value[aiMessageIndex].isWriting = false;
                  currentWritingStep.value = '';
                }
              } else if (data.type === "interrupt") {
                // resume 后又遇到 interrupt
                const interruptData = data.content;
                const interruptValue = Array.isArray(interruptData) && interruptData[0]?.value
                  ? interruptData[0].value
                  : {};
                const interruptType = interruptValue.type || 'human_review';

                if (interruptType === 'clarification') {
                  // 澄清提问类型
                  const question = interruptValue.question || interruptValue.message || '请补充说明您的需求';
                  messages.value[aiMessageIndex].content = question;
                  messages.value[aiMessageIndex].isClarification = true;
                  messages.value[aiMessageIndex].clarificationQuestion = question;
                  isWaitingClarification.value = true;
                } else {
                  // 草稿审阅类型
                  const draft = interruptValue.draft || '';
                  messages.value[aiMessageIndex].content = draft;
                  messages.value[aiMessageIndex].isReviewing = true;
                  messages.value[aiMessageIndex].draft = draft;
                  isWaitingReview.value = true;
                }
                messages.value[aiMessageIndex].currentStep = '';
                messages.value[aiMessageIndex].isWriting = false;
                isLoading.value = false;
                currentWritingStep.value = '';
                reader.releaseLock();
                return;
              } else if (data.type === "content" || data.type === "text") {
                // 只显示 is_display 节点的内容
                if (data.content && data.is_display) {
                  if (!receivedFirstContent) {
                    receivedFirstContent = true;
                    isLoading.value = false;
                  }
                  messages.value[aiMessageIndex].content += data.content;
                }
              }
            } catch (e) {
              console.warn('Failed to parse JSON:', jsonStr, e);
            }
          }
        }
      }
      reader.releaseLock();

    } catch (error: any) {
      // 如果是用户主动暂停，不删除消息
      if (error.name === 'AbortError') {
        console.log('流式响应已暂停');
        // 保留已生成的内容，只清除加载状态
        if (messages.value[aiMessageIndex]) {
          messages.value[aiMessageIndex].isWriting = false;
          messages.value[aiMessageIndex].currentStep = '';
        }
        return;
      }
      console.error('Resume error:', error);
      throw error;
    } finally {
      isLoading.value = false;
      abortController = null;
    }
  };

  // 暂停流式响应
  const pauseStream = () => {
    isPaused.value = true;
    
    // 中止前端的 fetch 请求，后端会自动检测到并取消 LangGraph 任务
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    
    isLoading.value = false;
    currentWritingStep.value = '';
    
    // 重置所有消息的写作状态
    messages.value.forEach(msg => {
      if (msg.isWriting) {
        msg.isWriting = false;
        msg.currentStep = '';
      }
    });
  };

  // 设置消息为审阅状态
  const setMessageReviewing = (index: number, draft: string) => {
    messages.value[index].isReviewing = true;
    messages.value[index].draft = draft;
    isWaitingReview.value = true;
  };

  // 清除文章内容
  const clearArticle = () => {
    articleContent.value = '';
    isArticleWriting.value = false;
    currentNode.value = '';
  };

  /**
   * 提交用户对澄清问题的回答
   * @param answer - 用户的回答内容
   */
  const submitClarification = async (answer: string) => {
    if (!userStore.token || !answer.trim() || !currentConversationId.value) return;

    isLoading.value = true;
    isWaitingClarification.value = false;

    // 找到当前正在等待澄清的消息并更新状态
    const clarifyingIndex = messages.value.findIndex(m => m.isClarification);
    if (clarifyingIndex !== -1) {
      messages.value[clarifyingIndex].isClarification = false;
    }

    // 添加用户回答消息
    messages.value.push({ role: 'human', content: answer, sources: [] });

    const aiMessageIndex = messages.value.length;
    messages.value.push({ role: 'ai', content: '', sources: [], isReviewing: false, draft: '' });

    try {
      // 创建新的 AbortController
      abortController = new AbortController();

      // 使用流式接口恢复执行
      const response = await fetchWithAuth(`${import.meta.env.VITE_API_URL}/api/chat/chat/resume/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          conversation_id: currentConversationId.value,
          action: 'clarify', 
          answer 
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let receivedFirstContent = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            const jsonStr = trimmedLine.slice(6);
            if (jsonStr.trim() === '' || jsonStr.trim() === '[DONE]') continue;

            try {
              const data = JSON.parse(jsonStr);
              if (data.finished) {
                break;
              }
              if (data.type === "sources") {
                if (data.content && Array.isArray(data.content)) {
                  messages.value[aiMessageIndex].sources = data.content;
                }
              } else if (data.type === "node_start") {
                // 中间步骤开始，更新状态
                if (!data.is_display) {
                  messages.value[aiMessageIndex].currentStep = data.label || '';
                  messages.value[aiMessageIndex].isWriting = true;
                  currentWritingStep.value = data.label || '';
                } else {
                  messages.value[aiMessageIndex].currentStep = '';
                  messages.value[aiMessageIndex].isWriting = false;
                  currentWritingStep.value = '';
                }
              } else if (data.type === "interrupt") {
                // resume 后又遇到 interrupt
                const interruptData = data.content;
                const interruptValue = Array.isArray(interruptData) && interruptData[0]?.value
                  ? interruptData[0].value
                  : {};
                const interruptType = interruptValue.type || 'human_review';

                if (interruptType === 'clarification') {
                  const question = interruptValue.question || interruptValue.message || '请补充说明您的需求';
                  messages.value[aiMessageIndex].content = question;
                  messages.value[aiMessageIndex].isClarification = true;
                  messages.value[aiMessageIndex].clarificationQuestion = question;
                  isWaitingClarification.value = true;
                } else {
                  const draft = interruptValue.draft || '';
                  messages.value[aiMessageIndex].content = draft;
                  messages.value[aiMessageIndex].isReviewing = true;
                  messages.value[aiMessageIndex].draft = draft;
                  isWaitingReview.value = true;
                }
                messages.value[aiMessageIndex].currentStep = '';
                messages.value[aiMessageIndex].isWriting = false;
                isLoading.value = false;
                currentWritingStep.value = '';
                reader.releaseLock();
                return;
              } else if (data.type === "content" || data.type === "text") {
                // 只显示 is_display 节点的内容
                if (data.content && data.is_display) {
                  if (!receivedFirstContent) {
                    receivedFirstContent = true;
                    isLoading.value = false;
                  }
                  messages.value[aiMessageIndex].content += data.content;
                }
              }
            } catch (e) {
              console.warn('Failed to parse JSON:', jsonStr, e);
            }
          }
        }
      }
      reader.releaseLock();

    } catch (error: any) {
      // 如果是用户主动暂停，不删除消息
      if (error.name === 'AbortError') {
        console.log('流式响应已暂停');
        if (messages.value[aiMessageIndex]) {
          messages.value[aiMessageIndex].isWriting = false;
          messages.value[aiMessageIndex].currentStep = '';
        }
        return;
      }
      console.error('Submit clarification error:', error);
      throw error;
    } finally {
      isLoading.value = false;
      abortController = null;
    }
  };

  return {
    messages,
    isLoading,
    isWaitingReview,
    isWaitingClarification,
    currentWritingStep,
    isPaused,
    // 会话相关状态
    conversations,
    currentConversationId,
    // 文章相关状态
    articleContent,
    isArticleWriting,
    currentNode,
    // 会话管理方法
    loadConversations,
    createConversation,
    switchConversation,
    deleteConversation,
    renameConversation,
    // 聊天方法
    loadChatHistory,
    sendMessage,
    resumeWriting,
    submitClarification,
    pauseStream,
    setMessageReviewing,
    clearArticle,
    // 重置方法
    resetStore: () => {
      messages.value = [];
      conversations.value = [];
      currentConversationId.value = null;
      articleContent.value = '';
      isArticleWriting.value = false;
      currentNode.value = '';
      isLoading.value = false;
      isWaitingReview.value = false;
      isWaitingClarification.value = false;
      currentWritingStep.value = '';
      isPaused.value = false;
    },
  };
});
