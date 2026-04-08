<script setup lang="ts">
/**
 * Hero 组件 - 显示欢迎标题和描述（Perplexity 风格）
 */
</script>

<template>
  <div class="mb-12 text-center">
    <!-- Logo 头部 - 更简洁的圆形图标 -->
    <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-emerald-50 to-indigo-50 mb-8">
      <i class="fa-solid fa-robot text-4xl bg-gradient-to-r from-emerald-500 to-indigo-500 bg-clip-text text-transparent" />
    </div>

    <!-- 标题 - 更大字号 -->
    <h1 class="text-4xl sm:text-5xl font-bold text-slate-900 mb-4 leading-tight">
      你好，我是安信工的 AI 助手
    </h1>

    <!-- 描述 - 更浅的颜色 -->
    <p class="text-gray-400 text-lg sm:text-xl max-w-2xl mx-auto leading-relaxed">
      我掌握人工智能专业培养方案与专业课教案的全部内容，随时为你解答专业学习的各种问题
    </p>
  </div>
</template>