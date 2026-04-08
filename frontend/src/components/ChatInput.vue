<template>
  <div class="chat-input-wrapper">
    <div class="relative flex items-end gap-2 p-3 bg-white border border-slate-200 rounded-2xl shadow-sm focus-within:border-blue-400 focus-within:shadow-md transition-all">
      <!-- 文本输入区 -->
      <textarea
        ref="textareaRef"
        v-model="inputText"
        @keydown="handleKeydown"
        @input="autoResize"
        :placeholder="placeholder"
        :disabled="disabled"
        rows="1"
        class="flex-1 resize-none bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none leading-relaxed max-h-32 overflow-y-auto"
      />

      <!-- 字数统计 -->
      <span v-if="inputText.length > 100" class="text-xs text-slate-400 self-end mb-0.5 whitespace-nowrap">
        {{ inputText.length }}/500
      </span>

      <!-- 发送按钮 -->
      <button
        @click="handleSend"
        :disabled="!canSend"
        class="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-xl transition-all"
        :class="canSend
          ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
          : 'bg-slate-100 text-slate-400 cursor-not-allowed'"
      >
        <i v-if="loading" class="fa-solid fa-spinner fa-spin text-sm" />
        <i v-else class="fa-solid fa-paper-plane text-sm" />
      </button>
    </div>

    <!-- 快捷提示 -->
    <p class="text-xs text-slate-400 mt-2 text-center">
      Enter 发送，Shift + Enter 换行
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';

const props = withDefaults(defineProps<{
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  maxLength?: number;
}>(), {
  placeholder: '输入你的问题...',
  disabled: false,
  loading: false,
  maxLength: 500,
});

const emit = defineEmits<{
  send: [text: string];
}>();

const inputText = ref('');
const textareaRef = ref<HTMLTextAreaElement | null>(null);

const canSend = computed(() => {
  return inputText.value.trim().length > 0 && !props.disabled && !props.loading;
});

function handleSend() {
  if (!canSend.value) return;
  const text = inputText.value.trim();
  if (text.length > props.maxLength) return;
  emit('send', text);
  inputText.value = '';
  nextTick(() => autoResize());
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}

function autoResize() {
  const el = textareaRef.value;
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 128) + 'px';
}

/** 外部可调用：聚焦输入框 */
function focus() {
  textareaRef.value?.focus();
}

/** 外部可调用：设置输入内容 */
function setText(text: string) {
  inputText.value = text;
  nextTick(() => autoResize());
}

onMounted(() => {
  focus();
});

defineExpose({ focus, setText });
</script>

<style scoped>
textarea::-webkit-scrollbar {
  width: 4px;
}
textarea::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
}
</style>
