<script setup lang="ts">
import { RouterView } from 'vue-router';
import { useNetworkStatus } from '@/composables/useNetworkStatus';
import PWAPrompt from '@/components/PWAPrompt.vue';

const { isOnline } = useNetworkStatus();

document.title = '安信工 AI 助手 - 人工智能专业知识工作台';
</script>

<template>
  <div class="min-h-screen overflow-hidden font-inter text-slate-900 antialiased">
    <Transition name="slide-down">
      <div
        v-if="!isOnline"
        class="fixed left-0 right-0 top-0 z-[9999] bg-red-500 py-2 text-center text-sm font-medium text-white shadow-lg"
      >
        网络连接已断开，请检查当前网络设置。
      </div>
    </Transition>

    <RouterView v-slot="{ Component, route }">
      <Transition name="route-fade" mode="out-in">
        <component :is="Component" :key="route.fullPath" />
      </Transition>
    </RouterView>

    <PWAPrompt />
  </div>
</template>

<style>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

.route-fade-enter-active,
.route-fade-leave-active {
  transition:
    opacity var(--motion-duration-base, 320ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-base, 320ms) var(--motion-ease-standard, ease),
    filter var(--motion-duration-base, 320ms) var(--motion-ease-standard, ease);
}

.route-fade-enter-from,
.route-fade-leave-to {
  opacity: 0;
  transform: translate3d(0, 12px, 0);
  filter: blur(8px);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app {
  height: 100%;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
  -webkit-box-shadow: 0 0 0 30px white inset !important;
  -webkit-text-fill-color: #334155 !important;
  transition: background-color 5000s ease-in-out 0s;
}

.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}
</style>
