import { ref, onMounted, onUnmounted, type Ref } from 'vue';

/**
 * 动画状态类型
 */
export type AnimationState = 'idle' | 'entering' | 'entered' | 'leaving' | 'left';

/**
 * 动画配置选项
 */
export interface AnimationOptions {
  duration?: number;
  delay?: number;
  easing?: string;
}

/**
 * 通用动画 composable
 * 提供元素进入/离开动画的控制
 */
export function useAnimation(options: AnimationOptions = {}) {
  const { duration = 300, delay = 0 } = options;
  
  const state = ref<AnimationState>('idle');
  const isVisible = ref(false);
  
  const enter = () => {
    state.value = 'entering';
    isVisible.value = true;
    
    setTimeout(() => {
      state.value = 'entered';
    }, duration + delay);
  };
  
  const leave = () => {
    state.value = 'leaving';
    
    setTimeout(() => {
      state.value = 'idle';
      isVisible.value = false;
    }, duration);
  };
  
  const toggle = () => {
    if (isVisible.value) {
      leave();
    } else {
      enter();
    }
  };
  
  return {
    state,
    isVisible,
    enter,
    leave,
    toggle,
  };
}

/**
 * 交错动画 composable
 * 为列表项添加依次出现的动画效果
 */
export function useStaggerAnimation(itemCount: Ref<number>, baseDelay = 50) {
  const delays = ref<number[]>([]);
  
  const updateDelays = () => {
    delays.value = Array.from({ length: itemCount.value }, (_, i) => i * baseDelay);
  };
  
  onMounted(updateDelays);
  
  // 监听 itemCount 变化
  const stopWatch = () => {
    // cleanup if needed
  };
  
  onUnmounted(stopWatch);
  
  const getDelay = (index: number) => {
    return delays.value[index] || 0;
  };
  
  return {
    delays,
    getDelay,
    updateDelays,
  };
}

/**
 * 滚动触发动画 composable
 * 当元素进入视口时触发动画
 */
export function useScrollAnimation(threshold = 0.1) {
  const elementRef = ref<HTMLElement | null>(null);
  const isIntersecting = ref(false);
  let observer: IntersectionObserver | null = null;
  
  onMounted(() => {
    if (!elementRef.value) return;
    
    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            isIntersecting.value = true;
            // 只触发一次
            observer?.unobserve(entry.target);
          }
        });
      },
      { threshold }
    );
    
    observer.observe(elementRef.value);
  });
  
  onUnmounted(() => {
    observer?.disconnect();
  });
  
  return {
    elementRef,
    isIntersecting,
  };
}

/**
 * 打字机效果 composable
 */
export function useTypewriter(text: Ref<string>, speed = 30) {
  const displayText = ref('');
  const isTyping = ref(false);
  let currentIndex = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  
  const startTyping = () => {
    if (!text.value) return;
    
    isTyping.value = true;
    currentIndex = 0;
    displayText.value = '';
    
    const type = () => {
      if (currentIndex < text.value.length) {
        displayText.value += text.value[currentIndex];
        currentIndex++;
        timer = setTimeout(type, speed);
      } else {
        isTyping.value = false;
      }
    };
    
    type();
  };
  
  const stopTyping = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    isTyping.value = false;
    displayText.value = text.value;
  };
  
  const resetTyping = () => {
    stopTyping();
    displayText.value = '';
    currentIndex = 0;
  };
  
  onUnmounted(() => {
    if (timer) {
      clearTimeout(timer);
    }
  });
  
  return {
    displayText,
    isTyping,
    startTyping,
    stopTyping,
    resetTyping,
  };
}

/**
 * 鼠标悬停动画 composable
 */
export function useHoverAnimation() {
  const isHovered = ref(false);
  const elementRef = ref<HTMLElement | null>(null);
  
  const onMouseEnter = () => {
    isHovered.value = true;
  };
  
  const onMouseLeave = () => {
    isHovered.value = false;
  };
  
  onMounted(() => {
    const el = elementRef.value;
    if (!el) return;
    
    el.addEventListener('mouseenter', onMouseEnter);
    el.addEventListener('mouseleave', onMouseLeave);
  });
  
  onUnmounted(() => {
    const el = elementRef.value;
    if (!el) return;
    
    el.removeEventListener('mouseenter', onMouseEnter);
    el.removeEventListener('mouseleave', onMouseLeave);
  });
  
  return {
    elementRef,
    isHovered,
  };
}
