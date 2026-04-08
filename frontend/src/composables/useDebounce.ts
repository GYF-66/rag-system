import { ref, watch, type Ref } from 'vue';

/**
 * 闃叉姈 Hook
 * @param value 闇€瑕侀槻鎶栫殑鍊? * @param delay 寤惰繜鏃堕棿锛堟绉掞級
 * @returns 闃叉姈鍚庣殑鍊? */
export function useDebounce<T>(value: Ref<T>, delay: number = 300): Ref<T> {
  const debouncedValue = ref(value.value) as Ref<T>;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  watch(value, (newValue) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      debouncedValue.value = newValue;
    }, delay);
  }, { flush: 'sync' });

  return debouncedValue;
}

/**
 * 闃叉姈鍑芥暟
 * @param fn 闇€瑕侀槻鎶栫殑鍑芥暟
 * @param delay 寤惰繜鏃堕棿锛堟绉掞級
 * @returns 闃叉姈鍚庣殑鍑芥暟
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number = 300
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

