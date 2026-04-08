<template>
  <div class="min-h-screen workspace-bg">
    <TopNavbar />
    <main class="px-4 py-6 sm:px-6">
      <div class="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <LibraryMasthead
          eyebrow="404"
          title="页面未找到"
          description="这个地址没有对应的校园 RAG 页面。你可以返回公共首页，或直接进入工作台继续发起检索增强问答。"
          icon="fa-solid fa-compass"
          :pills="['公共首页', '专业学习工作台', '教学支持场景']"
        />

        <section class="workspace-card reveal-item rounded-[30px] px-6 py-16 text-center" v-reveal>
          <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-[28px] bg-[rgba(171,104,70,0.12)] text-[#8d4c32]">
            <i class="fa-solid fa-map-location-dot text-3xl" />
          </div>
          <p class="mt-6 text-sm font-semibold uppercase tracking-[0.24em] text-[rgba(112,83,69,0.72)]">Campus RAG</p>
          <h1 class="mt-3 text-5xl font-black text-[#2b1f1c]">404</h1>
          <p class="mx-auto mt-4 max-w-2xl text-sm leading-7 text-[rgba(76,58,49,0.78)]">建议从首页重新选择专业主题，或者直接进入工作台询问培养方案、课程体系、奖助信息与毕业设计等问题。</p>
          <div class="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <router-link to="/" class="rounded-full bg-[#8b472f] px-6 py-3 text-sm font-semibold text-white">返回公共首页</router-link>
            <router-link to="/manual" class="rounded-full border border-[rgba(120,85,63,0.16)] px-6 py-3 text-sm font-semibold text-[rgba(76,58,49,0.82)]">进入 专业学习工作台</router-link>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import LibraryMasthead from '@/components/LibraryMasthead.vue';
import TopNavbar from '@/components/TopNavbar.vue';
</script>
