<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

interface Props {
  modelValue: string;
  placeholder?: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '询问人工智能专业相关问题，例如：机器学习课程学什么？',
  disabled: false,
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  submit: [];
  'focus-toggle': [];
}>();

const inputRef = ref<HTMLInputElement | null>(null);
const isFocusMenuOpen = ref(false);
const placeholders = [
  '询问人工智能专业相关问题，例如：机器学习课程学什么？',
  '你可以问：如何申请国家奖学金？',
  '你可以问：毕业设计有哪些要求？',
  '你可以问：考研和就业该怎么规划？',
];
const currentPlaceholder = ref('');
let placeholderIndex = 0;
let charIndex = 0;
let isDeleting = false;
let typingTimer: number | undefined;

const canSubmit = computed(() => props.modelValue.trim().length > 0 && !props.disabled);
const chevronStyle = computed(() => ({ transform: `rotate(${isFocusMenuOpen.value ? 180 : 0}deg)` }));

function scheduleTyping(delay: number) {
  typingTimer = window.setTimeout(typePlaceholder, delay);
}

function typePlaceholder() {
  const currentText = placeholders[placeholderIndex];

  if (isDeleting) {
    currentPlaceholder.value = currentText.slice(0, Math.max(charIndex - 1, 0));
    charIndex -= 1;
  } else {
    currentPlaceholder.value = currentText.slice(0, charIndex + 1);
    charIndex += 1;
  }

  let typeSpeed = isDeleting ? 30 : 60;

  if (!isDeleting && charIndex === currentText.length) {
    isDeleting = true;
    typeSpeed = 2200;
  } else if (isDeleting && charIndex <= 0) {
    isDeleting = false;
    placeholderIndex = (placeholderIndex + 1) % placeholders.length;
    typeSpeed = 500;
  }

  scheduleTyping(typeSpeed);
}

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
}

function handleSubmit(event?: Event) {
  event?.preventDefault();
  if (canSubmit.value) {
    emit('submit');
  }
}

function handleFocusToggle() {
  isFocusMenuOpen.value = !isFocusMenuOpen.value;
  emit('focus-toggle');
}

function focus() {
  inputRef.value?.focus();
}

function blur() {
  inputRef.value?.blur();
}

onMounted(() => {
  if (props.placeholder === placeholders[0]) {
    scheduleTyping(1000);
    return;
  }

  currentPlaceholder.value = props.placeholder;
});

onUnmounted(() => {
  if (typeof typingTimer === 'number') {
    window.clearTimeout(typingTimer);
  }
});

defineExpose({ focus, blur });
</script>

<template>
  <div class="w-full max-w-2xl" data-testid="home-search-box">
    <form class="search-wrapper flex items-center px-6 py-4" @submit="handleSubmit">
      <div class="flex-shrink-0 text-slate-400">
        <i class="fa-solid fa-magnifying-glass text-xl" />
      </div>

      <input
        ref="inputRef"
        :value="modelValue"
        :placeholder="currentPlaceholder || placeholder"
        :disabled="disabled"
        class="flex-1 ml-4 text-lg text-slate-900 placeholder-slate-400 outline-none bg-transparent font-medium transition-all"
        autocomplete="off"
        data-testid="search-input"
        @input="handleInput"
      >

      <div class="ml-4 flex items-center space-x-2">
        <button
          type="button"
          :class="[
            'focus-btn flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold',
            isFocusMenuOpen ? 'active' : 'text-slate-600',
          ]"
          @click="handleFocusToggle"
        >
          <i class="fa-solid fa-crosshairs text-sm" />
          <span class="hidden sm:inline">聚焦 Focus</span>
          <i class="fa-solid fa-chevron-down text-xs ml-0.5 transition-transform duration-200" :style="chevronStyle" />
        </button>
      </div>

      <div class="w-px h-6 bg-slate-200 mx-2" />

      <button
        type="submit"
        :disabled="!canSubmit"
        :class="[
          'submit-btn ml-3 w-11 h-11 flex items-center justify-center text-white',
          canSubmit ? 'cursor-pointer' : 'cursor-not-allowed opacity-40',
        ]"
        data-testid="search-submit"
      >
        <i class="fa-solid fa-arrow-up text-base" />
      </button>
    </form>

    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="isFocusMenuOpen"
        class="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden z-50"
      >
        <div class="p-2">
          <button class="w-full flex items-center space-x-3 px-4 py-3 rounded-xl hover:bg-slate-50 transition-colors duration-200 text-left">
            <div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
              <i class="fa-solid fa-globe text-emerald-600" />
            </div>
            <div class="flex-1">
              <div class="text-sm font-medium text-slate-900">全部知识库</div>
              <div class="text-xs text-slate-500">搜索所有可用资源</div>
            </div>
            <i class="fa-solid fa-check text-emerald-600" />
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.search-wrapper {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1.5px solid rgba(0, 0, 0, 0.06);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02);
  position: relative;
}

.search-wrapper:focus-within {
  border-color: #10b981;
  box-shadow: 0 8px 32px rgba(16, 185, 129, 0.12), 0 2px 8px rgba(0, 0, 0, 0.04);
  transform: translateY(-2px);
}

.focus-btn {
  background: rgba(0, 0, 0, 0.04);
  border-radius: 10px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.focus-btn:hover {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
}

.focus-btn.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(16, 185, 129, 0.08) 100%);
  color: #6366f1;
}

.submit-btn {
  background: linear-gradient(135deg, #10b981 0%, #6366f1 100%);
  border-radius: 12px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.24);
}

.submit-btn:not(:disabled):hover {
  transform: scale(1.05);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.32);
}

.submit-btn:not(:disabled):active {
  transform: scale(0.98);
}
</style>



