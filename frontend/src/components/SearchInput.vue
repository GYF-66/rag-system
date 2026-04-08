<script setup lang="ts">
import { ref, computed, watch } from 'vue';

interface Props {
  modelValue: string;
  placeholder?: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请输入您的问题，例如：奖学金申请条件...',
  disabled: false,
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  submit: [];
}>();

const inputRef = ref<HTMLInputElement | null>(null);

/**
 * 输入框焦点
 */
const focus = () => {
  inputRef.value?.focus();
};

const blur = () => {
  inputRef.value?.blur();
};

/**
 * 提交状态
 */
const canSubmit = computed(() => {
  return props.modelValue.trim().length > 0 && !props.disabled;
});

/**
 * 监听 modelValue 变化
 */
watch(() => props.modelValue, (newValue) => {
  emit('update:modelValue', newValue);
});

/**
 * 处理提交
 */
const handleSubmit = () => {
  if (canSubmit.value) {
    emit('submit');
  }
};

/**
 * 暴露方法
 */
defineExpose({
  focus,
  blur,
});
</script>

<template>
  <form @submit.prevent="handleSubmit">
    <div class="relative group">
      <div class="absolute inset-y-0 left-0 pl-5 sm:pl-6 flex items-center pointer-events-none">
        <i class="fa-solid fa-magnifying-glass text-slate-400 text-lg sm:text-xl" />
      </div>
      <input
        ref="inputRef"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        class="w-full pl-12 sm:pl-14 pr-16 sm:pr-20 py-5 sm:py-6 text-base sm:text-lg bg-white rounded-full shadow-deep border-2 border-slate-200 focus:border-emerald-500 focus:outline-none focus:ring-4 focus:ring-emerald-500/20 transition-all duration-300 placeholder:text-slate-400 disabled:opacity-50 disabled:cursor-not-allowed"
        @input="(e: Event) => emit('update:modelValue', (e.target as HTMLInputElement).value)"
      >
      <button
        type="submit"
        :disabled="!canSubmit"
        :class="[
          'absolute inset-y-0 right-2 my-1 px-4 sm:px-5 rounded-full font-medium text-sm sm:text-base transition-all duration-200 cursor-pointer',
          canSubmit
            ? 'bg-emerald-500 text-white hover:bg-emerald-600'
            : 'bg-slate-200 text-slate-700 hover:bg-emerald-500 hover:text-white'
        ]"
        aria-label="搜索"
      >
        <i class="fa-solid fa-arrow-right" />
      </button>
    </div>
  </form>
</template>