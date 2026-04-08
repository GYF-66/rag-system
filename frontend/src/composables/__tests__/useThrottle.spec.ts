import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ref } from 'vue';
import { useThrottle, throttle } from '@/composables/useThrottle';

describe('useThrottle', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useThrottle composable', () => {
    it('should throttle ref value changes', () => {
      const value = ref(0);
      const throttledValue = useThrottle(value, 300);

      expect(throttledValue.value).toBe(0);

      // First change should apply immediately
      value.value = 1;
      vi.advanceTimersByTime(0);
      expect(throttledValue.value).toBe(1);

      // Rapid changes within throttle period should be ignored
      value.value = 2;
      vi.advanceTimersByTime(100);
      expect(throttledValue.value).toBe(1);

      value.value = 3;
      vi.advanceTimersByTime(100);
      expect(throttledValue.value).toBe(1);

      // After throttle period, last value should apply
      vi.advanceTimersByTime(100);
      expect(throttledValue.value).toBe(3);
    });

    it('should use custom delay', () => {
      const value = ref('test');
      const throttledValue = useThrottle(value, 500);

      value.value = 'first';
      vi.advanceTimersByTime(0);
      expect(throttledValue.value).toBe('first');

      value.value = 'second';
      vi.advanceTimersByTime(300);
      expect(throttledValue.value).toBe('first');

      vi.advanceTimersByTime(200);
      expect(throttledValue.value).toBe('second');
    });
  });

  describe('throttle function', () => {
    it('should throttle function calls', () => {
      const fn = vi.fn();
      const throttledFn = throttle(fn, 300);

      // First call should execute immediately
      throttledFn('call1');
      expect(fn).toHaveBeenCalledTimes(1);
      expect(fn).toHaveBeenCalledWith('call1');

      // Calls within throttle period should be delayed
      throttledFn('call2');
      throttledFn('call3');
      expect(fn).toHaveBeenCalledTimes(1);

      // After throttle period, last call should execute
      vi.advanceTimersByTime(300);
      expect(fn).toHaveBeenCalledTimes(2);
      expect(fn).toHaveBeenLastCalledWith('call3');
    });

    it('should preserve function context', () => {
      const context = { value: 42 };
      const fn = vi.fn(function(this: typeof context) {
        return this.value;
      });
      const throttledFn = throttle(fn, 300);

      throttledFn.call(context);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should handle multiple arguments', () => {
      const fn = vi.fn();
      const throttledFn = throttle(fn, 300);

      throttledFn('x', 'y', 'z');
      expect(fn).toHaveBeenCalledWith('x', 'y', 'z');
    });
  });
});
