<template>
  <div v-if="hasError" class="flex flex-col items-center justify-center py-12 px-6">
    <div class="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4">
      <i class="fa-solid fa-triangle-exclamation text-2xl text-red-400" />
    </div>
    <h3 class="text-lg font-semibold text-slate-700 mb-1">{{ title }}</h3>
    <p class="text-sm text-slate-500 text-center max-w-sm mb-5">{{ message }}</p>
    <div class="flex gap-3">
      <button
        v-if="retryable"
        @click="handleRetry"
        class="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition"
      >
        <i class="fa-solid fa-rotate-right mr-1.5" />重试
      </button>
      <button
        @click="handleDismiss"
        class="px-5 py-2 bg-slate-100 text-slate-600 text-sm font-medium rounded-xl hover:bg-slate-200 transition"
      >
        关闭
      </button>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    message?: string;
    retryable?: boolean;
  }>(),
  {
    title: '出了点问题',
    message: '请稍后再试，或联系管理员获取帮助。',
    retryable: true,
  },
);

const emit = defineEmits<{
  retry: [];
  dismiss: [];
}>();

const hasError = defineModel<boolean>('error', { default: false });

function handleRetry() {
  hasError.value = false;
  emit('retry');
}

function handleDismiss() {
  hasError.value = false;
  emit('dismiss');
}
</script>
