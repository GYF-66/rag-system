import { ref, watch, type Ref } from 'vue';

/**
 * 鑺傛祦 Hook
 * @param value 闇€瑕佽妭娴佺殑鍊? * @param delay 寤惰繜鏃堕棿锛堟绉掞級
 * @returns 鑺傛祦鍚庣殑鍊? */
export function useThrottle<T>(value: Ref<T>, delay: number = 300): Ref<T> {
  const throttledValue = ref(value.value) as Ref<T>;
  let lastUpdate = -delay;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  watch(value, (newValue) => {
    const now = Date.now();

    if (now - lastUpdate >= delay) {
      throttledValue.value = newValue;
      lastUpdate = now;
    } else {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      timeoutId = setTimeout(() => {
        throttledValue.value = newValue;
        lastUpdate = Date.now();
      }, delay - (now - lastUpdate));
    }
  }, { flush: 'sync' });

  return throttledValue;
}

/**
 * 鑺傛祦鍑芥暟
 * @param fn 闇€瑕佽妭娴佺殑鍑芥暟
 * @param delay 寤惰繜鏃堕棿锛堟绉掞級
 * @returns 鑺傛祦鍚庣殑鍑芥暟
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  delay: number = 300
): (...args: Parameters<T>) => void {
  let lastCall = 0;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    const now = Date.now();

    if (now - lastCall >= delay) {
      fn.apply(this, args);
      lastCall = now;
    } else {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      timeoutId = setTimeout(() => {
        fn.apply(this, args);
        lastCall = Date.now();
      }, delay - (now - lastCall));
    }
  };
}

