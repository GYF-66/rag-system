<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import LibraryMasthead from '@/components/LibraryMasthead.vue';
import MessageBubble from '@/components/MessageBubble.vue';
import MobileNav from '@/components/MobileNav.vue';
import Sidebar from '@/components/Sidebar.vue';
import TopNavbar from '@/components/TopNavbar.vue';
import { apiClient } from '@/services/api';
import { useChatStore } from '@/stores/chat';

interface ManualChapter {
  id: string;
  title: string;
  icon: string;
  intro: string;
  items: string[];
}

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const { messages, isLoading, error: chatError, lastAttemptedMessage } = storeToRefs(chatStore);

const chatContainer = ref<HTMLElement | null>(null);
const inputMessage = ref('');
const serviceState = ref<'checking' | 'healthy' | 'warning'>('checking');
const showGuide = ref(true);
const completedBootstrapKey = ref('');
const pendingBootstrapKey = ref('');
const perspectiveMode = ref(false);
const processedBootstrapKeys = new Set<string>();

const quickQuestions = [
  'RAG 在人工智能专业知识问答里如何减少幻觉？',
  '人工智能专业的核心课程与实践环节如何安排？',
  '请解释来源片段、重排结果与最终回答之间的关系。',
  '毕业设计、实习与培养目标之间如何衔接？',
];

const chapters: ManualChapter[] = [
  {
    id: 'workflow',
    title: 'RAG 工作流',
    icon: 'fa-solid fa-diagram-project',
    intro: '从检索召回、片段重排到答案生成，关注每一步如何提升回答可信度。',
    items: ['检索增强是什么', '如何理解重排', '为什么展示来源', '怎样继续追问'],
  },
  {
    id: 'curriculum',
    title: 'AI 专业课程',
    icon: 'fa-solid fa-book-open-reader',
    intro: '围绕培养方案、课程地图与实践体系，快速组织专业问题。',
    items: ['培养目标', '核心课程', '实践教学', '学分结构'],
  },
  {
    id: 'student',
    title: '学习事务',
    icon: 'fa-solid fa-user-graduate',
    intro: '适合奖助学金、毕业设计、课程安排和日常学习支持类问题。',
    items: ['奖助学金', '毕业设计', '课程安排', '学习路径'],
  },
];

const connectionLabel = computed(() => {
  if (serviceState.value === 'checking') {
    return '正在检测知识服务状态…';
  }

  return serviceState.value === 'healthy'
    ? '知识服务状态正常，可以继续提问。'
    : '知识服务存在异常，但仍可继续提问或稍后重试。';
});

const connectionTone = computed(() => {
  if (serviceState.value === 'checking') {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }

  return serviceState.value === 'healthy'
    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
    : 'border-amber-200 bg-amber-50 text-amber-700';
});

const emptyStateVisible = computed(() => messages.value.length === 0 && !isLoading.value);

async function checkApiConnection() {
  serviceState.value = 'checking';

  try {
    await apiClient.healthCheck();
    serviceState.value = 'healthy';
  } catch {
    serviceState.value = 'warning';
  }
}

async function scrollToBottom() {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
}

async function sendMessage(prefilled?: string) {
  const message = (prefilled ?? inputMessage.value).trim();
  if (!message || isLoading.value) {
    return;
  }

  inputMessage.value = '';
  showGuide.value = false;

  try {
    if (perspectiveMode.value) {
      await chatStore.sendPerspectiveChat(message);
    } else {
      await chatStore.sendStreamingChat(message);
    }
    serviceState.value = 'healthy';
  } catch (error) {
    serviceState.value = 'warning';
    throw error;
  } finally {
    await scrollToBottom();
  }
}

async function retryLastMessage() {
  if (!lastAttemptedMessage.value || isLoading.value) {
    return;
  }
  await sendMessage(lastAttemptedMessage.value);
}

async function sendQuickQuestion(question: string) {
  inputMessage.value = question;
  await sendMessage(question);
}

async function handleManualTopic(chapterTitle: string, item: string) {
  await sendQuickQuestion(`请结合“${chapterTitle}”说明“${item}”在人工智能专业 RAG 场景中的具体要求。`);
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    void sendMessage();
  }
}

function handleQuickQuestionFromSidebar(question: string) {
  void sendQuickQuestion(question);
}

function handleNewChat() {
  chatStore.newConversation();
  inputMessage.value = '';
  showGuide.value = true;
  void scrollToBottom();
}

async function bootstrapFromRoute() {
  const query = typeof route.query.q === 'string' ? route.query.q.trim() : '';
  const bootstrapKey = `${route.path}::${query}`;

  if (
    !query
    || isLoading.value
    || processedBootstrapKeys.has(bootstrapKey)
    || pendingBootstrapKey.value === bootstrapKey
    || completedBootstrapKey.value === bootstrapKey
  ) {
    return;
  }

  processedBootstrapKeys.add(bootstrapKey);
  pendingBootstrapKey.value = bootstrapKey;

  try {
    await sendQuickQuestion(query);
    completedBootstrapKey.value = bootstrapKey;

    const nextQuery = { ...route.query };
    delete nextQuery.q;
    await router.replace({ path: route.path, query: nextQuery });
  } catch (error) {
    processedBootstrapKeys.delete(bootstrapKey);
    throw error;
  } finally {
    if (pendingBootstrapKey.value === bootstrapKey) {
      pendingBootstrapKey.value = '';
    }
  }
}

watch(
  () => route.query.q,
  () => {
    void bootstrapFromRoute();
  },
);

watch(messages, () => {
  void scrollToBottom();
}, { deep: true });

onMounted(async () => {
  await checkApiConnection();
  await bootstrapFromRoute();
  await scrollToBottom();
});
</script>

<template>
  <div class="flex h-screen workspace-bg" data-testid="manual-page">
    <Sidebar @new-chat="handleNewChat" @quick-question="handleQuickQuestionFromSidebar" />

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <TopNavbar />

      <main class="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        <div class="mx-auto flex w-full max-w-7xl flex-col gap-6">
          <LibraryMasthead
            eyebrow="RAG Workspace"
            title="专业知识问答工作台"
            description="把检索增强、来源片段、思考过程和人工智能专业问题放进同一条工作流里，先看依据，再看结论。"
            icon="fa-solid fa-robot"
            :pills="['来源追踪', '专业问答', '连续追问', '可信解释']"
            :stats="[
              { label: '工作模式', value: perspectiveMode ? '多视角问答' : '流式 RAG' },
              { label: '应用场景', value: 'AI 专业知识' },
              { label: '交互方式', value: '检索后作答' },
            ]"
          >
            <template #aside>
              <div class="space-y-4 text-sm leading-7 text-[rgba(255,248,241,0.82)]">
                <div>
                  <p class="text-xs uppercase tracking-[0.24em] text-[rgba(255,248,241,0.56)]">Workflow</p>
                  <h2 class="mt-2 text-xl font-semibold text-white">先看到内容，再查看推理</h2>
                </div>
                <p>本页优先保证问答正文、思考面板和输入区始终可见。折叠卡、badge 和字体风格都保留，但不再影响核心内容显示。</p>
              </div>
            </template>
          </LibraryMasthead>

          <section class="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
            <aside class="workspace-card rounded-[30px] p-5">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Guide</p>
                  <h2 class="mt-2 text-xl font-black text-[#281d19]">开始提问</h2>
                </div>
                <button
                  type="button"
                  class="rounded-full border border-[rgba(120,85,63,0.16)] px-3 py-1 text-xs font-semibold text-[rgba(86,64,53,0.82)] transition hover:-translate-y-0.5 hover:bg-[rgba(178,120,88,0.08)]"
                  @click="showGuide = !showGuide"
                >
                  {{ showGuide ? '已查看' : '查看指引' }}
                </button>
              </div>

              <div
                class="mt-4 rounded-2xl border px-4 py-3 text-sm font-medium"
                :class="connectionTone"
                data-testid="connection-status"
                :data-connected="serviceState === 'healthy' ? 'true' : 'false'"
              >
                {{ connectionLabel }}
              </div>

              <div class="mt-5 space-y-3">
                <button
                  v-for="question in quickQuestions"
                  :key="question"
                  type="button"
                  class="quick-btn magnetic-card w-full rounded-2xl px-4 py-3 text-left text-sm font-medium"
                  data-testid="manual-quick-question"
                  @click="sendQuickQuestion(question)"
                >
                  {{ question }}
                </button>
              </div>

              <div v-if="showGuide" class="mt-6 space-y-4">
                <article
                  v-for="chapter in chapters"
                  :key="chapter.id"
                  class="glow-hover rounded-[24px] border border-[rgba(120,85,63,0.14)] bg-[rgba(255,252,247,0.88)] p-4"
                >
                  <div class="flex items-center gap-3">
                    <span class="flex h-10 w-10 items-center justify-center rounded-2xl bg-[rgba(171,104,70,0.12)] text-[#8f4c31]">
                      <i :class="chapter.icon" />
                    </span>
                    <div>
                      <h3 class="font-semibold text-[#352622]">{{ chapter.title }}</h3>
                      <p class="text-xs leading-6 text-[rgba(85,65,56,0.76)]">{{ chapter.intro }}</p>
                    </div>
                  </div>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <button
                      v-for="item in chapter.items"
                      :key="item"
                      type="button"
                      class="rounded-full border border-[rgba(120,85,63,0.16)] px-3 py-1.5 text-xs font-semibold text-[rgba(83,62,52,0.82)] transition hover:-translate-y-0.5 hover:bg-[rgba(171,104,70,0.08)]"
                      @click="handleManualTopic(chapter.title, item)"
                    >
                      {{ item }}
                    </button>
                  </div>
                </article>
              </div>
            </aside>

            <section class="workspace-card flex min-h-[720px] flex-col overflow-hidden rounded-[30px]">
              <div ref="chatContainer" class="flex-1 space-y-4 overflow-y-auto px-5 py-5 sm:px-6" data-testid="chat-message-list">
                <div v-if="emptyStateVisible" class="grid gap-4 md:grid-cols-2" data-testid="manual-empty-state">
                  <article class="glow-hover rounded-[28px] border border-[rgba(120,85,63,0.14)] bg-[rgba(255,252,247,0.9)] p-6">
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">How to use</p>
                    <h2 class="mt-2 text-2xl font-black text-[#271b18]">把问题放进一条可解释的 RAG 链路</h2>
                    <p class="mt-3 text-sm leading-7 text-[rgba(75,58,50,0.78)]">适合提问人工智能专业课程安排、培养目标、毕业设计要求，也适合解释来源片段和检索依据。</p>
                  </article>

                  <article class="rounded-[28px] bg-[rgba(43,28,21,0.9)] p-6 text-white">
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(255,248,241,0.58)]">Recommended</p>
                    <div class="mt-3 space-y-3 text-sm leading-7 text-[rgba(255,248,241,0.8)]">
                      <p>示例：请结合人工智能专业培养方案，说明核心课程、实践环节与毕业设计之间的关系。</p>
                      <p>示例：为什么这个回答会引用这些来源片段？请解释重排依据与可信度。</p>
                    </div>
                  </article>
                </div>

                <MessageBubble
                  v-for="message in messages"
                  :key="message.id"
                  :message="message"
                />

                <div v-if="chatError" class="rounded-[24px] border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700" data-testid="chat-error">
                  {{ chatError }}
                  <button
                    type="button"
                    class="ml-3 rounded-full border border-red-300 px-3 py-1 font-semibold text-red-700 transition hover:bg-red-100"
                    data-testid="chat-retry"
                    @click="retryLastMessage"
                  >
                    重试上一条问题
                  </button>
                </div>
              </div>

              <div class="border-t border-[rgba(120,85,63,0.14)] bg-[rgba(255,251,246,0.92)] px-5 py-4 sm:px-6">
                <div class="magnetic-card rounded-[26px] border border-[rgba(120,85,63,0.16)] bg-white/90 p-3 shadow-[0_18px_48px_rgba(75,52,39,0.08)]">
                  <textarea
                    v-model="inputMessage"
                    rows="3"
                    class="min-h-[110px] w-full resize-none bg-transparent px-3 py-2 text-sm leading-7 text-[#2f231f] outline-none placeholder:text-[rgba(112,83,69,0.56)]"
                    placeholder="输入你的问题，例如：人工智能专业的核心课程与实践环节如何安排？"
                    data-testid="chat-input"
                    @keydown="handleKeydown"
                  />

                  <div class="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div class="flex flex-wrap items-center gap-3">
                      <p class="text-xs text-[rgba(94,73,63,0.72)]">Enter 发送，Shift + Enter 换行</p>
                      <button
                        type="button"
                        :class="[
                          'flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition',
                          perspectiveMode
                            ? 'border-[rgba(146,86,56,0.4)] bg-[rgba(171,104,70,0.1)] text-[#8f4c31]'
                            : 'border-[rgba(120,85,63,0.16)] text-[rgba(94,73,63,0.6)] hover:bg-[rgba(171,104,70,0.06)]',
                        ]"
                        data-testid="perspective-toggle"
                        @click="perspectiveMode = !perspectiveMode"
                      >
                        <i class="fa-solid fa-layer-group" />
                        <span>{{ perspectiveMode ? '多视角已开启' : '多视角' }}</span>
                      </button>
                    </div>

                    <button
                      type="button"
                      class="submit-btn magnetic-card flex h-11 min-w-[124px] items-center justify-center rounded-full px-5 text-sm font-semibold text-white"
                      data-testid="chat-send"
                      :disabled="!inputMessage.trim() || isLoading"
                      @click="sendMessage()"
                    >
                      {{ isLoading ? '生成中…' : perspectiveMode ? '多视角提问' : '发送问题' }}
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </section>
        </div>
      </main>

      <MobileNav />
    </div>
  </div>
</template>
