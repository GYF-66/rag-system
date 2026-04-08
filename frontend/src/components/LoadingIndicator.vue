<script setup lang="ts">
// Loading indicator component - 无需 props
</script>

<template>
  <div class="flex gap-4">
    <div class="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-slate-700 flex items-center justify-center">
      <i class="fa-solid fa-robot text-white text-sm sm:text-base" />
    </div>
    <div class="bg-white border border-slate-200 p-4 rounded-2xl rounded-bl-none">
      <div class="flex gap-1">
        <span class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms" />
        <span class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms" />
        <span class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms" />
      </div>
    </div>
  </div>
</template>