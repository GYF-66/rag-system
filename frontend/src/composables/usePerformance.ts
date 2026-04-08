import { ref, onUnmounted } from 'vue';

/**
 * 防抖 composable
 */
export function useDebounce<T extends (...args: unknown[]) => void>(fn: T, delay = 300) {
  let timer: ReturnType<typeof setTimeout> | null = null;

  const debouncedFn = (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };

  const cancel = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };

  onUnmounted(cancel);

  return { debouncedFn, cancel };
}

/**
 * 节流 composable
 */
export function useThrottle<T extends (...args: unknown[]) => void>(fn: T, interval = 200) {
  let lastTime = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const throttledFn = (...args: Parameters<T>) => {
    const now = Date.now();
    const remaining = interval - (now - lastTime);

    if (remaining <= 0) {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      lastTime = now;
      fn(...args);
    } else if (!timer) {
      timer = setTimeout(() => {
        lastTime = Date.now();
        timer = null;
        fn(...args);
      }, remaining);
    }
  };

  onUnmounted(() => {
    if (timer) clearTimeout(timer);
  });

  return { throttledFn };
}

/**
 * 响应式防抖值
 */
export function useDebouncedRef<T>(initialValue: T, delay = 300) {
  const value = ref(initialValue) as ReturnType<typeof ref<T>>;
  const debouncedValue = ref(initialValue) as ReturnType<typeof ref<T>>;
  let timer: ReturnType<typeof setTimeout> | null = null;

  function update(newVal: T) {
    value.value = newVal as T;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      debouncedValue.value = newVal as T;
    }, delay);
  }

  onUnmounted(() => {
    if (timer) clearTimeout(timer);
  });

  return { value, debouncedValue, update };
}
