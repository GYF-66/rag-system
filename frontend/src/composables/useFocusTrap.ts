import { ref, watch, onMounted, onUnmounted, type Ref } from 'vue';

/**
 * 焦点陷阱 Hook
 * 用于模态框、侧边栏等需要限制焦点范围的组件
 * 
 * @param containerRef 容器元素引用
 * @param isActive 是否激活焦点陷阱
 * @returns 焦点陷阱控制方法
 */
export function useFocusTrap(
  containerRef: Ref<HTMLElement | null>,
  isActive: Ref<boolean> = ref(true)
) {
  const previousActiveElement = ref<HTMLElement | null>(null);

  /**
   * 获取容器内所有可聚焦元素
   */
  const getFocusableElements = (): HTMLElement[] => {
    if (!containerRef.value) return [];

    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ');

    return Array.from(
      containerRef.value.querySelectorAll<HTMLElement>(focusableSelectors)
    ).filter((el) => {
      // 过滤掉不可见元素
      return el.offsetParent !== null;
    });
  };

  /**
   * 处理 Tab 键导航
   */
  const handleKeyDown = (e: KeyboardEvent) => {
    if (!isActive.value || !containerRef.value) return;

    // 只处理 Tab 键
    if (e.key !== 'Tab') return;

    const focusableElements = getFocusableElements();
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    const activeElement = document.activeElement as HTMLElement;

    // Shift + Tab：从第一个元素跳到最后一个
    if (e.shiftKey && activeElement === firstElement) {
      e.preventDefault();
      lastElement.focus();
      return;
    }

    // Tab：从最后一个元素跳到第一个
    if (!e.shiftKey && activeElement === lastElement) {
      e.preventDefault();
      firstElement.focus();
      return;
    }
  };

  /**
   * 激活焦点陷阱
   */
  const activate = () => {
    if (!containerRef.value) return;

    // 保存当前焦点元素
    previousActiveElement.value = document.activeElement as HTMLElement;

    // 聚焦到容器内第一个可聚焦元素
    const focusableElements = getFocusableElements();
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    // 添加键盘事件监听
    document.addEventListener('keydown', handleKeyDown);
  };

  /**
   * 停用焦点陷阱
   */
  const deactivate = () => {
    // 移除键盘事件监听
    document.removeEventListener('keydown', handleKeyDown);

    // 恢复之前的焦点
    if (previousActiveElement.value) {
      previousActiveElement.value.focus();
      previousActiveElement.value = null;
    }
  };

  /**
   * 监听激活状态变化
   */
  watch(isActive, (active) => {
    if (active) {
      activate();
    } else {
      deactivate();
    }
  });

  /**
   * 组件挂载时激活（如果需要）
   */
  onMounted(() => {
    if (isActive.value) {
      activate();
    }
  });

  /**
   * 组件卸载时清理
   */
  onUnmounted(() => {
    deactivate();
  });

  return {
    activate,
    deactivate,
    getFocusableElements,
  };
}
