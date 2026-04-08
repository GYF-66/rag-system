<template>
  <div class="space-y-4 animate-pulse">
    <!-- 头像 + 消息骨架 -->
    <div v-for="i in lines" :key="i" class="flex gap-3" :class="i % 2 === 0 ? 'flex-row-reverse' : ''">
      <div v-if="avatar" class="w-10 h-10 rounded-full bg-slate-200 flex-shrink-0" />
      <div class="flex-1 space-y-2" :class="i % 2 === 0 ? 'flex flex-col items-end' : ''">
        <div class="h-4 bg-slate-200 rounded-lg" :style="{ width: randomWidth() }" />
        <div class="h-4 bg-slate-200 rounded-lg" :style="{ width: randomWidth() }" />
        <div v-if="i % 2 !== 0" class="h-4 bg-slate-200 rounded-lg" :style="{ width: randomWidth() }" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  lines?: number;
  avatar?: boolean;
  animated?: boolean;
}>(), {
  lines: 3,
  avatar: true,
  animated: true,
});

function randomWidth(): string {
  return `${Math.floor(Math.random() * 40) + 40}%`;
}
</script>
