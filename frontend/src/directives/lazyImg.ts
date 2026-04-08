import type { Directive } from 'vue';

/**
 * v-lazy-img 图片懒加载指令
 * 使用 IntersectionObserver 实现
 *
 * 用法: <img v-lazy-img="imageUrl" />
 */
export const vLazyImg: Directive<HTMLImageElement, string> = {
  mounted(el, binding) {
    const placeholder = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200"%3E%3Crect fill="%23f1f5f9" width="300" height="200"/%3E%3C/svg%3E';

    el.src = placeholder;
    el.style.transition = 'opacity 0.3s ease';

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const img = entry.target as HTMLImageElement;
            img.src = binding.value;
            img.onload = () => {
              img.style.opacity = '1';
            };
            img.onerror = () => {
              img.src = placeholder;
            };
            observer.unobserve(img);
          }
        }
      },
      { rootMargin: '100px' },
    );

    observer.observe(el);

    // 存储 observer 以便卸载时清理
    (el as unknown as Record<string, unknown>).__lazyObserver = observer;
  },

  unmounted(el) {
    const observer = (el as unknown as Record<string, unknown>).__lazyObserver as IntersectionObserver | undefined;
    if (observer) {
      observer.disconnect();
    }
  },
};
