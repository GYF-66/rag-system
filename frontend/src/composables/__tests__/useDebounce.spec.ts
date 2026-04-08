import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ref } from 'vue';
import { useDebounce, debounce } from '@/composables/useDebounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useDebounce composable', () => {
    it('should debounce ref value changes', () => {
      const value = ref('initial');
      const debouncedValue = useDebounce(value, 300);

      expect(debouncedValue.value).toBe('initial');

      value.value = 'updated';
      expect(debouncedValue.value).toBe('initial');

      vi.advanceTimersByTime(300);
      expect(debouncedValue.value).toBe('updated');
    });

    it('should cancel previous timeout on rapid changes', () => {
      const value = ref(0);
      const debouncedValue = useDebounce(value, 300);

      value.value = 1;
      vi.advanceTimersByTime(100);
      
      value.value = 2;
      vi.advanceTimersByTime(100);
      
      value.value = 3;
      vi.advanceTimersByTime(100);

      // Should still be initial value
      expect(debouncedValue.value).toBe(0);

      // After full delay, should have latest value
      vi.advanceTimersByTime(200);
      expect(debouncedValue.value).toBe(3);
    });

    it('should use custom delay', () => {
      const value = ref('test');
      const debouncedValue = useDebounce(value, 500);

      value.value = 'changed';
      vi.advanceTimersByTime(300);
      expect(debouncedValue.value).toBe('test');

      vi.advanceTimersByTime(200);
      expect(debouncedValue.value).toBe('changed');
    });
  });

  describe('debounce function', () => {
    it('should debounce function calls', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 300);

      debouncedFn('arg1');
      debouncedFn('arg2');
      debouncedFn('arg3');

      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(300);
      expect(fn).toHaveBeenCalledTimes(1);
      expect(fn).toHaveBeenCalledWith('arg3');
    });

    it('should preserve function context', () => {
      const context = { value: 42 };
      const fn = vi.fn(function(this: typeof context) {
        return this.value;
      });
      const debouncedFn = debounce(fn, 300);

      debouncedFn.call(context);
      vi.advanceTimersByTime(300);

      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should handle multiple arguments', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 300);

      debouncedFn('a', 'b', 'c');
      vi.advanceTimersByTime(300);

      expect(fn).toHaveBeenCalledWith('a', 'b', 'c');
    });
  });
});
