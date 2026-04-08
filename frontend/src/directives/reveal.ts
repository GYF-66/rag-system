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
    el.classList.add('reveal-item');
    el.style.setProperty('--reveal-delay', `${delay}ms`);

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-revealed');
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
  },
  unmounted(el) {
    const observer = Reflect.get(el, '__revealObserver__') as IntersectionObserver | undefined;
    observer?.disconnect();
  },
};
