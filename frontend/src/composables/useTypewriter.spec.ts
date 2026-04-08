import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useTypewriter } from './useTypewriter';

// Mock onUnmounted since we're not in a component context
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue');
  return { ...actual as object, onUnmounted: vi.fn() };
});

describe('useTypewriter', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('初始状态为空', () => {
    const { displayText, isTyping } = useTypewriter();
    expect(displayText.value).toBe('');
    expect(isTyping.value).toBe(false);
  });

  it('start 开始打字效果', () => {
    const { displayText, isTyping, start } = useTypewriter(10);
    start('Hello');

    expect(isTyping.value).toBe(true);
    expect(displayText.value).not.toBe('Hello'); // 还没打完
  });

  it('打字完成后 isTyping 变为 false', () => {
    const { displayText, isTyping, start } = useTypewriter(5);
    start('Hi');

    // 快进足够时间让打字完成
    vi.advanceTimersByTime(500);

    expect(displayText.value).toBe('Hi');
    expect(isTyping.value).toBe(false);
  });

  it('stop 立即显示全部文本', () => {
    const { displayText, isTyping, start, stop } = useTypewriter(50);
    start('一段很长的文本内容');

    stop();

    expect(displayText.value).toBe('一段很长的文本内容');
    expect(isTyping.value).toBe(false);
  });

  it('reset 清空所有状态', () => {
    const { displayText, isTyping, start, reset } = useTypewriter(10);
    start('测试');
    vi.advanceTimersByTime(200);

    reset();

    expect(displayText.value).toBe('');
    expect(isTyping.value).toBe(false);
  });

  it('连续调用 start 会重置之前的打字', () => {
    const { displayText, start } = useTypewriter(10);
    start('第一段');
    vi.advanceTimersByTime(50);

    start('第二段');
    vi.advanceTimersByTime(500);

    expect(displayText.value).toBe('第二段');
  });
});
