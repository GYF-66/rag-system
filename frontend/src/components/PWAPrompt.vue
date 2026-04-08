<template>
  <Teleport to="body">
    <!-- 更新提示 -->
    <Transition name="slide-up">
      <div
        v-if="needRefresh"
        class="pwa-prompt"
        role="alert"
        aria-live="polite"
      >
        <div class="pwa-prompt-content">
          <div class="pwa-prompt-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
              />
            </svg>
          </div>
          <div class="pwa-prompt-text">
            <h3>发现新版本</h3>
            <p>点击更新以获取最新功能和修复</p>
          </div>
          <div class="pwa-prompt-actions">
            <button
              class="pwa-btn pwa-btn-primary"
              @click="updateApp"
              aria-label="更新应用"
            >
              更新
            </button>
            <button
              class="pwa-btn pwa-btn-secondary"
              @click="closeUpdatePrompt"
              aria-label="稍后更新"
            >
              稍后
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 离线就绪提示 -->
    <Transition name="slide-up">
      <div
        v-if="offlineReady"
        class="pwa-prompt pwa-prompt-success"
        role="status"
        aria-live="polite"
      >
        <div class="pwa-prompt-content">
          <div class="pwa-prompt-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div class="pwa-prompt-text">
            <h3>离线就绪</h3>
            <p>应用已缓存，可以离线使用</p>
          </div>
          <div class="pwa-prompt-actions">
            <button
              class="pwa-btn pwa-btn-secondary"
              @click="closeOfflinePrompt"
              aria-label="关闭提示"
            >
              知道了
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { usePWA } from '@/composables/usePWA';

const { needRefresh, offlineReady, updateApp, closeUpdatePrompt, closeOfflinePrompt } = usePWA();
</script>

<style scoped>
.pwa-prompt {
  position: fixed;
  bottom: var(--spacing-6);
  right: var(--spacing-6);
  z-index: var(--z-tooltip);
  max-width: 400px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: var(--spacing-4);
}

.pwa-prompt-success {
  border-color: var(--color-success);
}

.pwa-prompt-content {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-3);
}

.pwa-prompt-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  color: var(--color-primary-600);
}

.pwa-prompt-success .pwa-prompt-icon {
  color: var(--color-success);
}

.pwa-prompt-text {
  flex: 1;
  min-width: 0;
}

.pwa-prompt-text h3 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.pwa-prompt-text p {
  margin: var(--spacing-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.pwa-prompt-actions {
  display: flex;
  gap: var(--spacing-2);
  margin-top: var(--spacing-3);
}

.pwa-btn {
  padding: var(--spacing-2) var(--spacing-4);
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.pwa-btn-primary {
  background: var(--color-primary-600);
  color: white;
}

.pwa-btn-primary:hover {
  background: var(--color-primary-700);
}

.pwa-btn-secondary {
  background: var(--color-neutral-100);
  color: var(--color-text-primary);
}

.pwa-btn-secondary:hover {
  background: var(--color-neutral-200);
}

/* 动画 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all var(--transition-base);
}

.slide-up-enter-from {
  transform: translateY(100%);
  opacity: 0;
}

.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* 响应式 */
@media (max-width: 640px) {
  .pwa-prompt {
    left: var(--spacing-4);
    right: var(--spacing-4);
    bottom: var(--spacing-4);
    max-width: none;
  }
}
</style>
