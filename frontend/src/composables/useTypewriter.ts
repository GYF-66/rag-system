import { ref, onUnmounted } from 'vue';

/**
 * 打字机效果 composable
 * @param speed 每个字符的间隔（ms）
 */
export function useTypewriter(speed = 20) {
  const displayText = ref('');
  const isTyping = ref(false);
  let timer: ReturnType<typeof setTimeout> | null = null;
  let fullText = '';
  let index = 0;

  function start(text: string) {
    stop();
    fullText = text;
    index = 0;
    displayText.value = '';
    isTyping.value = true;
    tick();
  }

  function tick() {
    if (index < fullText.length) {
      // 每次追加 1-3 个字符，让效果更自然
      const chunk = Math.min(Math.floor(Math.random() * 3) + 1, fullText.length - index);
      displayText.value += fullText.slice(index, index + chunk);
      index += chunk;
      timer = setTimeout(tick, speed + Math.random() * 15);
    } else {
      isTyping.value = false;
    }
  }

  function stop() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    if (fullText && index < fullText.length) {
      displayText.value = fullText;
    }
    isTyping.value = false;
  }

  function reset() {
    stop();
    displayText.value = '';
    fullText = '';
    index = 0;
  }

  onUnmounted(() => stop());

  return { displayText, isTyping, start, stop, reset };
}
