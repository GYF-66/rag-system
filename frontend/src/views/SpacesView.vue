<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import LibraryMasthead from '@/components/LibraryMasthead.vue';
import MobileNav from '@/components/MobileNav.vue';
import Sidebar from '@/components/Sidebar.vue';
import TopNavbar from '@/components/TopNavbar.vue';
import { DEMO_MODE } from '@/router';
import { apiClient, type Space } from '@/services/api';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();
const spaces = ref<Space[]>([]);
const isLoading = ref(false);
const error = ref('');

const isDemoReadonly = computed(() => DEMO_MODE && !authStore.isAuthenticated);

async function loadSpaces() {
  try {
    isLoading.value = true;
    error.value = '';
    const response = await apiClient.getSpaces();
    spaces.value = response.spaces ?? [];
  } catch (err) {
    error.value = err instanceof Error ? err.message : '知识空间加载失败';
    spaces.value = [];
  } finally {
    isLoading.value = false;
  }
}

function openSpace(spaceId: string) {
  router.push(`/space/${spaceId}`);
}

function handleQuickQuestion(question: string) {
  router.push({ path: '/manual', query: { q: question } });
}

function handleNewChat() {
  router.push('/manual');
}

onMounted(() => {
  void loadSpaces();
});
</script>

<template>
  <div class="flex h-screen workspace-bg">
    <Sidebar @quick-question="handleQuickQuestion" @new-chat="handleNewChat" />

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <TopNavbar />

      <main class="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        <div class="mx-auto flex w-full max-w-7xl flex-col gap-6">
          <LibraryMasthead
            eyebrow="Spaces"
            title="知识空间"
            description="把专题资料、课程说明和结构化知识入口组织成容器，用于承接更稳定的 RAG 检索场景。"
            icon="fa-regular fa-folder-open"
            :pills="['知识容器', '专题检索', '空间详情', '工作台联动']"
            :stats="[
              { label: '空间数量', value: String(spaces.length) },
              { label: '访问模式', value: isDemoReadonly ? '演示只读' : '已登录可用' },
              { label: '能力定位', value: 'RAG 检索入口' },
            ]"
          >
            <template #aside>
              <div class="space-y-3 text-sm leading-7 text-[rgba(255,248,241,0.82)]">
                <p class="text-xs uppercase tracking-[0.24em] text-[rgba(255,248,241,0.56)]">Spaces Mode</p>
                <p>空间页用于组织长期知识容器，不替代工作台，而是为工作台提供更稳定的知识入口。</p>
                <p v-if="isDemoReadonly">当前为演示只读模式，保留浏览路径，不开放私有管理能力。</p>
              </div>
            </template>
          </LibraryMasthead>

          <section class="workspace-card reveal-item rounded-[30px] p-5 sm:p-6" v-reveal>
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Repository</p>
                <h2 class="mt-2 text-2xl font-black text-[#281d19]">围绕主题组织知识检索入口</h2>
              </div>
              <button type="button" class="magnetic-card rounded-full bg-[#8b472f] px-5 py-3 text-sm font-semibold text-white" @click="handleNewChat">进入工作台提问</button>
            </div>

            <div v-if="isDemoReadonly" class="mt-5 rounded-[24px] border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-7 text-amber-800">
              演示模式下保留知识空间浏览与详情访问，用于说明 RAG 知识容器的组织方式；私有空间管理仍需登录后使用。
            </div>

            <div v-if="error" class="mt-5 rounded-[24px] border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
              {{ error }}
            </div>

            <div v-if="isLoading" class="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div v-for="index in 6" :key="index" class="h-44 animate-pulse rounded-[28px] border border-[rgba(120,85,63,0.12)] bg-[rgba(255,252,247,0.72)]" />
            </div>

            <div v-else-if="spaces.length > 0" class="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <article
                v-for="space in spaces"
                :key="space.id"
                class="group glow-hover reveal-item cursor-pointer rounded-[28px] border border-[rgba(120,85,63,0.14)] bg-[rgba(255,252,247,0.9)] p-5 shadow-[0_14px_38px_rgba(75,52,39,0.06)] transition duration-200 hover:-translate-y-1 hover:shadow-[0_22px_54px_rgba(75,52,39,0.12)]"
                v-reveal
                @click="openSpace(space.id)"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="flex h-14 w-14 items-center justify-center rounded-[20px] bg-[rgba(171,104,70,0.12)]">
                    <i :class="[space.icon, space.color, 'text-2xl']" />
                  </div>
                  <span class="rounded-full bg-[rgba(171,104,70,0.1)] px-3 py-1 text-xs font-semibold text-[#8d4c32]">{{ space.itemCount }} 项</span>
                </div>
                <h3 class="mt-5 text-xl font-semibold text-[#2f221f]">{{ space.name }}</h3>
                <p class="mt-3 min-h-[72px] text-sm leading-7 text-[rgba(76,58,49,0.78)]">{{ space.description || '该知识空间用于组织专题资料与检索入口，便于在工作台中快速发起专业问答。' }}</p>
                <div class="mt-5 flex items-center justify-between text-xs text-[rgba(112,83,69,0.7)]">
                  <span>更新于 {{ new Date(space.updatedAt).toLocaleDateString('zh-CN') }}</span>
                  <span class="transition group-hover:translate-x-1">查看详情</span>
                </div>
              </article>
            </div>

            <div v-else class="mt-6 reveal-item rounded-[30px] border border-dashed border-[rgba(120,85,63,0.2)] bg-[rgba(255,252,247,0.82)] px-6 py-14 text-center" v-reveal>
              <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-[rgba(171,104,70,0.1)] text-[#8d4c32]">
                <i class="fa-regular fa-folder-open text-2xl" />
              </div>
              <h3 class="mt-5 text-2xl font-black text-[#2b1f1c]">还没有可展示的知识空间</h3>
              <p class="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[rgba(76,58,49,0.78)]">你可以先通过工作台演示提问链路；当知识空间准备完成后，这里会承接更稳定的专题检索入口。</p>
              <button type="button" class="magnetic-card mt-6 rounded-full bg-[#8b472f] px-5 py-3 text-sm font-semibold text-white" @click="handleNewChat">返回工作台</button>
            </div>
          </section>
        </div>
      </main>

      <MobileNav />
    </div>
  </div>
</template>
