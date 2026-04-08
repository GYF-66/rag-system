<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import LibraryMasthead from '@/components/LibraryMasthead.vue';
import MobileNav from '@/components/MobileNav.vue';
import Sidebar from '@/components/Sidebar.vue';
import TopNavbar from '@/components/TopNavbar.vue';
import { useChatStore } from '@/stores/chat';
import { useHistoryStore } from '@/stores/history';
import type { ChatHistory } from '@/types';

const router = useRouter();
const historyStore = useHistoryStore();
const chatStore = useChatStore();

const showConfirmClear = ref(false);
const editingId = ref<string | null>(null);
const editTitle = ref('');

const totalMessages = computed(() => historyStore.items.reduce((sum, item) => sum + item.messages.length, 0));

function handleQuickQuestion(question: string) {
  router.push({ path: '/manual', query: { q: question } });
}

function handleNewChat() {
  router.push('/manual');
}

function restoreConversation(item: ChatHistory) {
  chatStore.restoreFromHistory(item.id);
  router.push('/manual');
}

function deleteItem(id: string) {
  historyStore.deleteItem(id);
}

function confirmClear() {
  historyStore.clearAll();
  showConfirmClear.value = false;
}

function startRename(item: ChatHistory) {
  editingId.value = item.id;
  editTitle.value = item.title;
}

function saveRename() {
  if (editingId.value && editTitle.value.trim()) {
    historyStore.renameItem(editingId.value, editTitle.value.trim());
  }
  editingId.value = null;
  editTitle.value = '';
}

function cancelRename() {
  editingId.value = null;
  editTitle.value = '';
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function messagePreview(item: ChatHistory): string {
  const assistantMessage = [...item.messages].reverse().find((message) => message.role === 'assistant');
  if (!assistantMessage) {
    return '该会话尚未生成助手回答。';
  }
  return assistantMessage.content.slice(0, 96) + (assistantMessage.content.length > 96 ? '...' : '');
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
            eyebrow="History"
            title="会话历史"
            description="管理已经完成的 RAG 问答记录，恢复对话上下文，继续围绕人工智能专业知识做追问与核验。"
            icon="fa-solid fa-clock-rotate-left"
            :pills="['恢复上下文', '重命名', '检索历史', '继续追问']"
            :stats="[
              { label: '历史会话', value: String(historyStore.totalCount) },
              { label: '累计消息', value: String(totalMessages) },
              { label: '检索方式', value: '按标题 / 内容' },
            ]"
          >
            <template #aside>
              <div class="space-y-3 text-sm leading-7 text-[rgba(255,248,241,0.82)]">
                <p class="text-xs uppercase tracking-[0.24em] text-[rgba(255,248,241,0.56)]">Archive</p>
                <p>历史页不只是记录列表，而是继续发起 RAG 追问的上下文入口。</p>
                <p>建议先恢复会话，再进入工作台继续补充问题和核验来源。</p>
              </div>
            </template>
          </LibraryMasthead>

          <section class="workspace-card reveal-item rounded-[30px] p-5 sm:p-6" v-reveal>
            <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Search</p>
                <h2 class="mt-2 text-2xl font-black text-[#281d19]">检索并整理你的问答轨迹</h2>
              </div>
              <div class="flex flex-col gap-3 sm:flex-row">
                <div class="relative min-w-[260px]">
                  <i class="fa-solid fa-magnifying-glass absolute left-4 top-1/2 -translate-y-1/2 text-[rgba(112,83,69,0.56)]" />
                  <input
                    v-model="historyStore.searchQuery"
                    type="text"
                    placeholder="搜索标题、问题或回答内容"
                    class="w-full rounded-full border border-[rgba(120,85,63,0.14)] bg-white px-11 py-3 text-sm text-[#2f231f] outline-none transition focus:border-[rgba(146,86,56,0.45)]"
                  />
                </div>
                <button
                  v-if="historyStore.totalCount > 0"
                  type="button"
                  class="magnetic-card rounded-full border border-[rgba(196,93,72,0.26)] px-5 py-3 text-sm font-semibold text-[#b34834] transition hover:bg-[rgba(196,93,72,0.08)]"
                  @click="showConfirmClear = true"
                >
                  清空全部历史
                </button>
              </div>
            </div>

            <div v-if="showConfirmClear" class="mt-5 flex flex-col gap-3 rounded-[24px] border border-red-200 bg-red-50 p-4 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-sm text-red-700">确认清空全部历史记录？该操作会删除本地保存的会话标题和消息快照。</p>
              <div class="flex gap-2">
                <button type="button" class="rounded-full border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700" @click="showConfirmClear = false">取消</button>
                <button type="button" class="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white" @click="confirmClear">确认清空</button>
              </div>
            </div>

            <div v-if="historyStore.groupedItems.length > 0" class="mt-6 space-y-8">
              <section v-for="group in historyStore.groupedItems" :key="group.label" class="space-y-3">
                <div class="flex items-center justify-between">
                  <h3 class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.7)]">{{ group.label }}</h3>
                  <span class="text-xs text-[rgba(112,83,69,0.62)]">{{ group.items.length }} 条</span>
                </div>

                <article
                  v-for="item in group.items"
                  :key="item.id"
                  class="glow-hover reveal-item rounded-[28px] border border-[rgba(120,85,63,0.14)] bg-[rgba(255,252,247,0.9)] p-5 shadow-[0_14px_38px_rgba(75,52,39,0.06)]"
                  v-reveal
                >
                  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div class="min-w-0 flex-1">
                      <div v-if="editingId === item.id" class="flex flex-col gap-3 sm:flex-row sm:items-center">
                        <input
                          v-model="editTitle"
                          type="text"
                          class="w-full rounded-full border border-[rgba(120,85,63,0.16)] bg-white px-4 py-2 text-sm text-[#2f231f] outline-none"
                          @keyup.enter="saveRename"
                        />
                        <div class="flex gap-2">
                          <button type="button" class="rounded-full bg-[#8b472f] px-4 py-2 text-sm font-semibold text-white" @click="saveRename">保存</button>
                          <button type="button" class="rounded-full border border-[rgba(120,85,63,0.16)] px-4 py-2 text-sm font-semibold text-[rgba(76,58,49,0.82)]" @click="cancelRename">取消</button>
                        </div>
                      </div>

                      <div v-else>
                        <div class="flex flex-wrap items-center gap-3">
                          <h4 class="text-lg font-semibold text-[#2e211d]">{{ item.title }}</h4>
                          <span class="rounded-full bg-[rgba(171,104,70,0.1)] px-3 py-1 text-xs font-semibold text-[#8d4c32]">{{ item.messages.length }} 条消息</span>
                          <span class="text-xs text-[rgba(112,83,69,0.68)]">更新于 {{ formatTime(item.updatedAt) }}</span>
                        </div>
                        <p class="mt-3 text-sm leading-7 text-[rgba(76,58,49,0.78)]">{{ messagePreview(item) }}</p>
                      </div>
                    </div>

                    <div class="flex flex-wrap gap-2">
                      <button type="button" class="rounded-full bg-[#8b472f] px-4 py-2 text-sm font-semibold text-white transition hover:-translate-y-0.5" @click="restoreConversation(item)">恢复会话</button>
                      <button type="button" class="rounded-full border border-[rgba(120,85,63,0.16)] px-4 py-2 text-sm font-semibold text-[rgba(76,58,49,0.82)]" @click="startRename(item)">重命名</button>
                      <button type="button" class="rounded-full border border-[rgba(196,93,72,0.24)] px-4 py-2 text-sm font-semibold text-[#b34834]" @click="deleteItem(item.id)">删除</button>
                    </div>
                  </div>
                </article>
              </section>
            </div>

            <div v-else class="mt-6 rounded-[30px] border border-dashed border-[rgba(120,85,63,0.2)] bg-[rgba(255,252,247,0.82)] px-6 py-14 text-center">
              <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-[rgba(171,104,70,0.1)] text-[#8d4c32]">
                <i class="fa-solid fa-folder-open text-2xl" />
              </div>
              <h3 class="mt-5 text-2xl font-black text-[#2b1f1c]">{{ historyStore.searchQuery ? '未找到匹配会话' : '还没有保存的会话历史' }}</h3>
              <p class="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[rgba(76,58,49,0.78)]">
                {{ historyStore.searchQuery ? '换一个关键词继续检索，或返回工作台查看最近的提问内容。' : '从首页示例问题或工作台发起一次提问后，这里会自动保存会话轨迹，方便继续追问。' }}
              </p>
              <button v-if="!historyStore.searchQuery" type="button" class="mt-6 rounded-full bg-[#8b472f] px-5 py-3 text-sm font-semibold text-white" @click="handleNewChat">进入工作台开始提问</button>
            </div>
          </section>
        </div>
      </main>

      <MobileNav />
    </div>
  </div>
</template>
