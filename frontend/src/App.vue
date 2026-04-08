<script setup lang="ts">
import { RouterView } from 'vue-router';
import { useNetworkStatus } from '@/composables/useNetworkStatus';
import PWAPrompt from '@/components/PWAPrompt.vue';

const { isOnline } = useNetworkStatus();

/**
 * 应用标题
 */
const appTitle = '安信工AI小助手 - 人工智能专业智能助手';

// 设置页面标题
document.title = appTitle;
</script>

<template>
  <div class="min-h-screen font-inter text-slate-900 antialiased overflow-hidden">
    <!-- 网络断线提示 -->
    <Transition name="slide-down">
      <div
        v-if="!isOnline"
        class="fixed top-0 left-0 right-0 z-[9999] bg-red-500 text-white text-center py-2 text-sm font-medium shadow-lg"
      >
        ⚠️ 网络连接已断开，请检查网络设置
      </div>
    </Transition>
    <RouterView v-slot="{ Component, route }">
      <Transition name="route-fade" mode="out-in">
        <component :is="Component" :key="route.fullPath" />
      </Transition>
    </RouterView>
    <!-- PWA 更新提示 -->
    <PWAPrompt />
  </div>
</template>

<style>
/* 网络断线提示过渡 */
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

/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 滚动条样式 */
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

/* 输入框自动填充样式 */
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
  -webkit-box-shadow: 0 0 0 30px white inset !important;
  -webkit-text-fill-color: #334155 !important;
  transition: background-color 5000s ease-in-out 0s;
}

/* 过渡效果 */
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}
</style>
