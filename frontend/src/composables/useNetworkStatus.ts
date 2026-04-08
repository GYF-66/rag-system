import { ref, onMounted, onUnmounted } from 'vue';

/**
 * 网络状态监听 composable
 */
export function useNetworkStatus() {
  const isOnline = ref(navigator.onLine);

  function handleOnline() {
    isOnline.value = true;
  }

  function handleOffline() {
    isOnline.value = false;
  }

  onMounted(() => {
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
  });

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  });

  return { isOnline };
}
