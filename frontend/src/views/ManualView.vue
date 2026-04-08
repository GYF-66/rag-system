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
const isConnected = ref(false);
const checkingConnection = ref(true);
const showGuide = ref(true);
const bootstrappedQuery = ref('');
const perspectiveMode = ref(false);

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
    intro: '从检索召回、片段重排到答案生成，关注每一步如何提高可信度。',
    items: ['检索增强是什么', '重排结果怎么看', '为什么要展示来源', '如何继续追问'],
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
    intro: '适合奖助学金、毕业设计、课程安排和日常学习支撑类问题。',
    items: ['奖助学金', '毕业设计', '课程安排', '学习路径'],
  },
];

const connectionLabel = computed(() => {
  if (checkingConnection.value) {
    return '正在检测知识服务状态';
  }
  return isConnected.value ? '知识服务已连接' : '知识服务暂不可用';
});

const connectionTone = computed(() => {
  if (checkingConnection.value) {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  return isConnected.value
    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
    : 'border-red-200 bg-red-50 text-red-700';
});

const emptyStateVisible = computed(() => messages.value.length === 0 && !isLoading.value);

async function checkApiConnection() {
  checkingConnection.value = true;
  try {
    await apiClient.healthCheck();
    isConnected.value = true;
  } catch {
    isConnected.value = false;
  } finally {
    checkingConnection.value = false;
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
      await chatStore.sendChat(message);
    }
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
  await sendQuickQuestion(`请结合${chapterTitle}说明“${item}”在人工智能专业 RAG 场景中的具体要求。`);
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
  if (!query || query === bootstrappedQuery.value) {
    return;
  }

  bootstrappedQuery.value = query;
  await sendQuickQuestion(query);
  await router.replace({ path: '/manual' });
}

watch(
  () => route.query.q,
  () => {
    void bootstrapFromRoute();
  },
);

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
            title="图书馆式知识工作台"
            description="把检索增强、来源片段和人工智能专业问题放进同一条工作流里，先找到依据，再组织回答。"
            icon="fa-solid fa-robot"
            :pills="['来源追踪', '专业问答', '连续追问', '知识可信度']"
            :stats="[
              { label: '工作模式', value: 'RAG 问答' },
              { label: '应用场景', value: 'AI 专业知识' },
              { label: '交互方式', value: '检索后回答' },
            ]"
          >
            <template #aside>
              <div class="space-y-4 text-sm leading-7 text-[rgba(255,248,241,0.82)]">
                <div>
                  <p class="text-xs uppercase tracking-[0.24em] text-[rgba(255,248,241,0.56)]">Workflow</p>
                  <h2 class="mt-2 text-xl font-semibold text-white">效率导向的专业问答入口</h2>
                </div>
                <p>适合演示培养方案、课程体系、奖助学金、毕业设计和学习路径类问题，也适合解释来源片段与重排结果。</p>
                <ul class="space-y-2 text-[rgba(255,248,241,0.72)]">
                  <li>先检索，再作答</li>
                  <li>展示来源卡片与结构化片段</li>
                  <li>支持连续追问与失败重试</li>
                </ul>
              </div>
            </template>
          </LibraryMasthead>

          <section class="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
            <aside v-reveal class="workspace-card reveal-item rounded-[30px] p-5">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Guide</p>
                  <h2 class="mt-2 text-xl font-black text-[#281d19]">开始提问</h2>
                </div>
                <button
                  type="button"
                  class="rounded-full border border-[rgba(120,85,63,0.16)] px-3 py-1 text-xs font-semibold text-[rgba(86,64,53,0.82)] transition hover:-translate-y-0.5 hover:bg-[rgba(178,120,88,0.08)]"
                  @click="showGuide = !showGuide"
                >
                  {{ showGuide ? '收起指引' : '查看指引' }}
                </button>
              </div>

              <div
                class="mt-4 rounded-2xl border px-4 py-3 text-sm font-medium"
                :class="connectionTone"
                data-testid="connection-status"
                :data-connected="isConnected ? 'true' : 'false'"
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
                  v-reveal
                  class="glow-hover reveal-item rounded-[24px] border border-[rgba(120,85,63,0.14)] bg-[rgba(255,252,247,0.88)] p-4"
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

            <section v-reveal="120" class="workspace-card reveal-item flex min-h-[720px] flex-col rounded-[30px] overflow-hidden">
              <div ref="chatContainer" class="flex-1 space-y-4 overflow-y-auto px-5 py-5 sm:px-6" data-testid="chat-message-list">
                <div v-if="emptyStateVisible" class="stagger-grid grid gap-4 md:grid-cols-2">
                  <article v-reveal class="glow-hover reveal-item rounded-[28px] border border-[rgba(120,85,63,0.14)] bg-[rgba(255,252,247,0.9)] p-6">
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">How to use</p>
                    <h2 class="mt-2 text-2xl font-black text-[#271b18]">把问题放进一条可解释的 RAG 链路</h2>
                    <p class="mt-3 text-sm leading-7 text-[rgba(75,58,50,0.78)]">适合提问人工智能专业课程安排、培养目标、毕业设计要求，也适合解释来源片段和检索依据。</p>
                  </article>
                  <article v-reveal="120" class="glow-hover reveal-item rounded-[28px] bg-[rgba(43,28,21,0.9)] p-6 text-white">
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(255,248,241,0.58)]">Recommended</p>
                    <div class="mt-3 space-y-3 text-sm leading-7 text-[rgba(255,248,241,0.8)]">
                      <p>示例：请结合人工智能专业培养方案，说明核心课程、实践环节与毕业设计的关系。</p>
                      <p>示例：为什么这个回答会引用这些来源片段？请解释其重排依据。</p>
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
                    重试上一次提问
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
                  <div class="mt-3 flex items-center justify-between gap-3">
                    <div class="flex items-center gap-3">
                      <p class="text-xs text-[rgba(94,73,63,0.72)]">Enter 发送，Shift + Enter 换行</p>
                      <button
                        type="button"
                        :class="[
                          'flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition',
                          perspectiveMode
                            ? 'border-[rgba(146,86,56,0.4)] bg-[rgba(171,104,70,0.1)] text-[#8f4c31]'
                            : 'border-[rgba(120,85,63,0.16)] text-[rgba(94,73,63,0.6)] hover:bg-[rgba(171,104,70,0.06)]',
                        ]"
                        data-testid="perspective-toggle"
                        @click="perspectiveMode = !perspectiveMode"
                      >
                        <span>🎓👨‍🏫</span>
                        <span>{{ perspectiveMode ? '多视角已开' : '多视角' }}</span>
                      </button>
                    </div>
                    <button
                      type="button"
                      class="submit-btn magnetic-card flex h-11 min-w-[124px] items-center justify-center rounded-full px-5 text-sm font-semibold text-white"
                      data-testid="chat-send"
                      :disabled="!inputMessage.trim() || isLoading"
                      @click="sendMessage()"
                    >
                      {{ isLoading ? '生成中...' : perspectiveMode ? '多视角提问' : '发送提问' }}
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


