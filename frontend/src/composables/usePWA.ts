import { ref, watch } from 'vue';
import { useRegisterSW } from 'virtual:pwa-register/vue';

export function usePWA() {
  const needRefresh = ref(false);
  const offlineReady = ref(false);

  const registration = useRegisterSW({
    onRegistered(_registration: ServiceWorkerRegistration | undefined) {
      // No-op: registration is only useful for diagnostics in development.
    },
    onRegisterError(_error: unknown) {
      // Keep the app usable even when service worker registration fails.
    },
    onNeedRefresh() {
      needRefresh.value = true;
    },
    onOfflineReady() {
      offlineReady.value = true;
    },
  });

  watch(registration.needRefresh, (value: boolean) => {
    needRefresh.value = value;
  });

  watch(registration.offlineReady, (value: boolean) => {
    offlineReady.value = value;
  });

  async function updateApp() {
    await registration.updateServiceWorker(true);
    needRefresh.value = false;
  }

  function closeUpdatePrompt() {
    needRefresh.value = false;
  }

  function closeOfflinePrompt() {
    offlineReady.value = false;
  }

  return {
    needRefresh,
    offlineReady,
    updateApp,
    closeUpdatePrompt,
    closeOfflinePrompt,
  };
}
