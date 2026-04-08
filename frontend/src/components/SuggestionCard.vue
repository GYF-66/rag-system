<script setup lang="ts">
import type { Suggestion } from '@/types';

interface Props {
  suggestion: Suggestion;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  click: [text: string];
}>();

const handleClick = () => {
  emit('click', props.suggestion.text);
};
</script>

<template>
  <button
    type="button"
    class="card-hover flex items-start gap-4 p-5 bg-white rounded-2xl border border-slate-200 hover:border-emerald-300 transition-all duration-300 cursor-pointer text-left"
    @click="handleClick"
  >
    <div class="flex-shrink-0 w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
      <i :class="['fa-solid', suggestion.icon, 'text-emerald-500 text-lg']" />
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-sm sm:text-base text-slate-700 font-medium">
        {{ suggestion.text }}
      </p>
      <p v-if="suggestion.description" class="text-xs text-slate-500 mt-1">
        {{ suggestion.description }}
      </p>
    </div>
  </button>
</template>

<style scoped>
.card-hover {
  transition: all 0.3s ease-in-out;
}
.card-hover:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.15);
  border-color: #10b981;
}
</style>