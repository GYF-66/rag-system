import { onMounted, onUnmounted } from 'vue';

/**
 * 键盘快捷键配置
 */
interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  handler: () => void;
  description?: string;
}

/**
 * 键盘快捷键 Hook
 * @param shortcuts 快捷键配置数组
 */
export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  const handleKeyDown = (e: KeyboardEvent) => {
    for (const shortcut of shortcuts) {
      const keyMatches = e.key.toLowerCase() === shortcut.key.toLowerCase();
      const ctrlMatches = !!shortcut.ctrl === (e.ctrlKey || e.metaKey);
      const metaMatches = !!shortcut.meta === (e.metaKey || e.ctrlKey);
      const shiftMatches = !!shortcut.shift === e.shiftKey;

      if (keyMatches && ctrlMatches && metaMatches && shiftMatches) {
        e.preventDefault();
        shortcut.handler();
        break;
      }
    }
  };

  onMounted(() => {
    document.addEventListener('keydown', handleKeyDown);
  });

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown);
  });

  return {
    shortcuts
  };
}

/**
 * 创建标准快捷键配置
 * @param options 选项
 */
export function createStandardShortcuts(options: {
  onSearchFocus?: () => void;
  onSubmit?: () => void;
  onClear?: () => void;
  onEscape?: () => void;
}): ShortcutConfig[] {
  const shortcuts: ShortcutConfig[] = [];

  if (options.onSearchFocus) {
    shortcuts.push({
      key: 'k',
      meta: true,
      handler: options.onSearchFocus,
      description: '聚焦搜索框'
    });
  }

  if (options.onSubmit) {
    shortcuts.push({
      key: 'Enter',
      handler: options.onSubmit,
      description: '提交搜索'
    });
  }

  if (options.onClear) {
    shortcuts.push({
      key: 'Escape',
      handler: options.onClear,
      description: '清空输入'
    });
  }

  if (options.onEscape) {
    shortcuts.push({
      key: 'Escape',
      handler: options.onEscape,
      description: '取消/失焦'
    });
  }

  return shortcuts;
}