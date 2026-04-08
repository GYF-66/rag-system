import { onMounted, onUnmounted, ref, watch } from 'vue';

export type Theme = 'light' | 'dark' | 'auto';

const THEME_STORAGE_KEY = 'app-theme';

export function useTheme() {
  const theme = ref<Theme>('auto');
  const isDark = ref(false);
  let cleanupSystemWatcher: (() => void) | null = null;

  function getSystemTheme(): 'light' | 'dark' {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(themeValue: Theme) {
    const effectiveTheme = themeValue === 'auto' ? getSystemTheme() : themeValue;
    isDark.value = effectiveTheme === 'dark';

    if (isDark.value) {
      document.documentElement.setAttribute('data-theme', 'dark');
      return;
    }

    document.documentElement.removeAttribute('data-theme');
  }

  function setTheme(nextTheme: Theme) {
    theme.value = nextTheme;
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    applyTheme(nextTheme);
  }

  function toggleTheme() {
    setTheme(isDark.value ? 'light' : 'dark');
  }

  function watchSystemTheme() {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = () => {
      if (theme.value === 'auto') {
        applyTheme('auto');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }

  onMounted(() => {
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
    if (savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'auto') {
      theme.value = savedTheme;
    }

    applyTheme(theme.value);
    cleanupSystemWatcher = watchSystemTheme();
  });

  onUnmounted(() => {
    cleanupSystemWatcher?.();
  });

  watch(theme, (nextTheme) => {
    applyTheme(nextTheme);
  });

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
  };
}
