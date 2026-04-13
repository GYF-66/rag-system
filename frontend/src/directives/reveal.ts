import type { Directive, DirectiveBinding } from 'vue';

type RevealBinding = number | { delay?: number } | undefined;

function resolveDelay(binding: DirectiveBinding<RevealBinding>): number {
  if (typeof binding.value === 'number') {
    return binding.value;
  }

  return binding.value?.delay ?? 0;
}

export const vReveal: Directive<HTMLElement, RevealBinding> = {
  mounted(el, binding) {
    const delay = resolveDelay(binding);
    const fallbackDelay = Math.max(delay + 900, 900);

    el.classList.add('reveal-item');
    el.style.setProperty('--reveal-delay', `${delay}ms`);
    el.setAttribute('data-reveal-ready', 'true');

    const reveal = () => {
      el.classList.add('is-revealed');

      const observer = Reflect.get(el, '__revealObserver__') as IntersectionObserver | undefined;
      observer?.disconnect();

      const timeoutId = Reflect.get(el, '__revealTimeout__') as number | undefined;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };

    if (typeof IntersectionObserver === 'undefined') {
      reveal();
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            reveal();
            observer.unobserve(entry.target);
          }
        }
      },
      {
        threshold: 0.16,
        rootMargin: '0px 0px -8% 0px',
      },
    );

    observer.observe(el);
    Reflect.set(el, '__revealObserver__', observer);
    Reflect.set(el, '__revealTimeout__', window.setTimeout(reveal, fallbackDelay));
  },
  unmounted(el) {
    const observer = Reflect.get(el, '__revealObserver__') as IntersectionObserver | undefined;
    observer?.disconnect();

    const timeoutId = Reflect.get(el, '__revealTimeout__') as number | undefined;
    if (timeoutId !== undefined) {
      window.clearTimeout(timeoutId);
    }
  },
};
