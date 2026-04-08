<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import LibraryMasthead from '@/components/LibraryMasthead.vue';
import MobileNav from '@/components/MobileNav.vue';
import Sidebar from '@/components/Sidebar.vue';
import SkeletonLoader from '@/components/SkeletonLoader.vue';
import TopNavbar from '@/components/TopNavbar.vue';
import { apiClient, type Space } from '@/services/api';

const router = useRouter();
const route = useRoute();

const spaceId = route.params.id as string;
const space = ref<Space | null>(null);
const isLoading = ref(true);
const error = ref('');

const mastheadStats = computed(() => {
  if (!space.value) {
    return [];
  }
  return [
    { label: '内容数量', value: String(space.value.itemCount) },
    { label: '最近更新', value: formatDate(space.value.updatedAt) },
    { label: '空间类型', value: '专题知识容器' },
  ];
});

onMounted(async () => {
  await loadSpace();
});

async function loadSpace() {
  try {
    isLoading.value = true;
    error.value = '';
    space.value = await apiClient.getSpaceById(spaceId);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载空间失败';
  } finally {
    isLoading.value = false;
  }
}

function goBack() {
  router.push('/spaces');
}

function formatDate(timestamp: string): string {
  return new Date(timestamp).toLocaleDateString('zh-CN');
}

function handleQuickQuestion(question: string) {
  router.push({ path: '/manual', query: { q: question } });
}

function handleNewChat() {
  if (space.value) {
    router.push({ path: '/manual', query: { q: `请结合知识空间“${space.value.name}”说明其可支持的人工智能专业问答主题。` } });
    return;
  }
  router.push('/manual');
}
</script>

<template>
  <div class="flex h-screen workspace-bg">
    <Sidebar @quick-question="handleQuickQuestion" @new-chat="handleNewChat" />

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <TopNavbar />

      <main class="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        <div class="mx-auto flex w-full max-w-7xl flex-col gap-6">
          <LibraryMasthead
            eyebrow="Space Detail"
            :title="space?.name || '知识空间详情'"
            :description="space?.description || '查看该知识空间的定位、更新时间与可支持的专业问答主题，并继续把问题带回工作台。'"
            icon="fa-solid fa-layer-group"
            :pills="['空间详情', '返回列表', '工作台联动']"
            :stats="mastheadStats"
          >
            <template #aside>
              <div class="space-y-3 text-sm leading-7 text-[rgba(255,248,241,0.82)]">
                <p class="text-xs uppercase tracking-[0.24em] text-[rgba(255,248,241,0.56)]">Detail</p>
                <p>空间详情页用于解释知识容器本身，而不是直接替代问答工作台。</p>
                <button type="button" class="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20" @click="goBack">返回空间列表</button>
              </div>
            </template>
          </LibraryMasthead>

          <section v-if="isLoading" class="workspace-card reveal-item rounded-[30px] p-6" v-reveal>
            <div class="space-y-4">
              <SkeletonLoader class="h-10 rounded-2xl" />
              <SkeletonLoader class="h-32 rounded-[28px]" />
              <SkeletonLoader class="h-48 rounded-[28px]" />
            </div>
          </section>

          <section v-else-if="error" class="workspace-card reveal-item rounded-[30px] px-6 py-14 text-center" v-reveal>
            <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-red-50 text-red-500">
              <i class="fa-solid fa-circle-exclamation text-2xl" />
            </div>
            <h2 class="mt-5 text-2xl font-black text-[#2b1f1c]">知识空间加载失败</h2>
            <p class="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[rgba(76,58,49,0.78)]">{{ error }}</p>
            <div class="mt-6 flex justify-center gap-3">
              <button type="button" class="rounded-full border border-[rgba(120,85,63,0.16)] px-5 py-3 text-sm font-semibold text-[rgba(76,58,49,0.82)]" @click="goBack">返回空间列表</button>
              <button type="button" class="rounded-full bg-[#8b472f] px-5 py-3 text-sm font-semibold text-white" @click="loadSpace">重新加载</button>
            </div>
          </section>

          <template v-else-if="space">
            <section class="workspace-card reveal-item rounded-[30px] p-6" v-reveal>
              <div class="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div class="flex items-start gap-4">
                  <div class="flex h-20 w-20 items-center justify-center rounded-[26px] bg-[rgba(171,104,70,0.12)]">
                    <i :class="[space.icon, space.color, 'text-4xl']" />
                  </div>
                  <div>
                    <h2 class="text-3xl font-black text-[#281d19]">{{ space.name }}</h2>
                    <p class="mt-3 max-w-3xl text-sm leading-7 text-[rgba(76,58,49,0.78)]">{{ space.description || '该空间用于承载专题资料、规范文本或结构化知识，以便为工作台提供更稳定的检索入口。' }}</p>
                  </div>
                </div>
                <div class="flex gap-3">
                  <button type="button" class="magnetic-card rounded-full border border-[rgba(120,85,63,0.16)] px-5 py-3 text-sm font-semibold text-[rgba(76,58,49,0.82)]" @click="goBack">返回列表</button>
                  <button type="button" class="magnetic-card rounded-full bg-[#8b472f] px-5 py-3 text-sm font-semibold text-white" @click="handleNewChat">以此空间发起提问</button>
                </div>
              </div>
            </section>

            <section class="workspace-card reveal-item rounded-[30px] p-6" v-reveal="120">
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Empty State</p>
              <h2 class="mt-2 text-2xl font-black text-[#281d19]">当前空间尚未展示具体条目</h2>
              <p class="mt-3 max-w-3xl text-sm leading-7 text-[rgba(76,58,49,0.78)]">当前前端保留空间详情结构和返回链路，未来可在这里挂接知识条目列表、文档摘要和片段入口；现在建议直接回到工作台，用这个空间名称发起提问。</p>
            </section>
          </template>
        </div>
      </main>

      <MobileNav />
    </div>
  </div>
</template>
