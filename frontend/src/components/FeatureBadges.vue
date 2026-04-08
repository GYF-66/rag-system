<script setup lang="ts">
/**
 * 特色标签类型
 */
interface FeatureBadge {
  icon: string;
  label: string;
  color: string;
}

/**
 * 特色标签数据
 */
const features: FeatureBadge[] = [
  {
    icon: 'fa-solid fa-shield-check',
    label: '权威数据源',
    color: 'text-emerald-500'
  },
  {
    icon: 'fa-solid fa-bolt',
    label: '智能问答',
    color: 'text-indigo-500'
  },
  {
    icon: 'fa-solid fa-clock',
    label: '24小时在线',
    color: 'text-emerald-500'
  }
];
</script>

<template>
  <div class="mt-12 flex flex-wrap items-center justify-center gap-5 sm:gap-8">
    <div
      v-for="(feature, index) in features"
      :key="feature.label"
      class="flex items-center space-x-2 text-sm text-slate-500"
    >
      <i :class="[feature.icon, feature.color]" />
      <span class="font-medium">{{ feature.label }}</span>
      <div
        v-if="index < features.length - 1"
        class="w-1 h-1 rounded-full bg-slate-300"
      />
    </div>
  </div>
</template>