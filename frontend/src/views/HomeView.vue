<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import LibraryBackdrop from '@/components/LibraryBackdrop.vue';
import SearchBox from '@/components/SearchBox.vue';
import TopNavbar from '@/components/TopNavbar.vue';
import { DEMO_MODE } from '@/router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();
const searchQuery = ref('');
const searchBoxRef = ref<InstanceType<typeof SearchBox> | null>(null);

const examplePrompts = [
  'RAG 在人工智能专业知识问答里如何减少幻觉？',
  '人工智能专业的核心课程与实践环节如何安排？',
  '奖学金申请通常需要哪些条件与材料？',
  '毕业设计有哪些关键要求与时间节点？',
];

const capabilityCards = [
  {
    title: 'Retrieval First',
    description: '先检索相关片段，再组织回答，并尽量返回来源与检索元数据。',
    icon: 'fa-solid fa-compass-drafting',
  },
  {
    title: '专业知识场景',
    description: '围绕人工智能专业培养方案、课程体系、学习路径与学生事务组织问题。',
    icon: 'fa-solid fa-brain',
  },
  {
    title: '可继续的工作台',
    description: '从首页检索直接带入问答工作台，保留提问上下文与连续体验。',
    icon: 'fa-solid fa-arrow-trend-up',
  },
];

const topicCards = [
  {
    title: 'RAG 技术理解',
    points: ['检索召回', '重排逻辑', '来源片段', '降低幻觉'],
    prompt: '请解释当前系统中的 RAG 工作流，包括检索、重排与回答生成。',
  },
  {
    title: '专业培养方案',
    points: ['培养目标', '毕业要求', '能力结构', '课程地图'],
    prompt: '请概述人工智能专业培养目标、毕业要求与能力结构。',
  },
  {
    title: '学习与事务支持',
    points: ['奖助学金', '学籍成绩', '实践安排', '毕业设计'],
    prompt: '请整理学生最常问的事务，包括奖助学金、实践安排和毕业设计。',
  },
];

const primaryActionLabel = computed(() => {
  if (authStore.isAuthenticated) return '继续进入学习工作台';
  if (DEMO_MODE) return '立即体验专业学习工作台';
  return '登录进入学习工作台';
});

const secondaryActionLabel = computed(() => {
  if (authStore.isAuthenticated) return '查看知识空间';
  if (DEMO_MODE) return '浏览专业主题';
  return '注册校园账号';
});

function submitSearch() {
  const query = searchQuery.value.trim();
  if (!query) {
    return;
  }

  router.push({
    path: '/manual',
    query: { q: query },
  });
}

function usePrompt(prompt: string) {
  searchQuery.value = prompt;
  submitSearch();
}

function handlePrimaryAction() {
  if (authStore.isAuthenticated || DEMO_MODE) {
    router.push('/manual');
    return;
  }

  router.push('/login');
}

function handleSecondaryAction() {
  if (authStore.isAuthenticated) {
    router.push('/spaces');
    return;
  }

  if (DEMO_MODE) {
    document.getElementById('topic-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  router.push('/register');
}

function openTopicPrompt(prompt: string) {
  searchQuery.value = prompt;
  submitSearch();
}

onMounted(() => {
  window.setTimeout(() => {
    searchBoxRef.value?.focus();
  }, 180);
});
</script>

<template>
  <div class="min-h-screen workspace-bg">
    <TopNavbar />

    <LibraryBackdrop variant="hero" intensity="high" class="landing-scene">
      <main class="landing-hero mx-auto flex min-h-[calc(72vh-5rem)] w-full max-w-7xl items-end px-6 pb-12 pt-8">
        <section class="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div class="landing-copy reveal-item is-revealed max-w-3xl">
            <div class="landing-chip magnetic-card">
              <i class="fa-solid fa-landmark" />
              <span>专业学习主视觉 · 人工智能专业 RAG 系统</span>
            </div>

            <h1 class="landing-title">
              让专业学习场景承载
              <span>RAG 技术与人工智能专业培养支持</span>
            </h1>
            <p class="landing-description">
              从培养方案、课程体系到奖助学金与毕业设计，把校园知识组织成可检索、可追溯、可继续提问的 RAG 工作流。
              先搜索，再进入工作台完成带来源的专业问答。
            </p>

            <div class="mt-8 max-w-3xl">
              <SearchBox
                ref="searchBoxRef"
                v-model="searchQuery"
                placeholder="试着输入：人工智能专业的核心课程与实践环节如何安排？"
                @submit="submitSearch"
              />
            </div>

            <div class="landing-actions mt-6 reveal-item is-revealed" style="--reveal-delay: 100ms">
              <button type="button" class="landing-primary magnetic-card" @click="handlePrimaryAction">
                <span>{{ primaryActionLabel }}</span>
                <i class="fa-solid fa-arrow-right-long" />
              </button>
              <button type="button" class="landing-secondary magnetic-card" @click="handleSecondaryAction">
                <span>{{ secondaryActionLabel }}</span>
              </button>
            </div>

            <div class="landing-prompts stagger-grid mt-6 reveal-item is-revealed" style="--reveal-delay: 180ms">
              <button
                v-for="prompt in examplePrompts"
                :key="prompt"
                type="button"
                class="landing-prompt magnetic-card"
                @click="usePrompt(prompt)"
              >
                {{ prompt }}
              </button>
            </div>
          </div>

          <aside class="landing-panel workspace-card reveal-item is-revealed rounded-[32px] p-6" style="--reveal-delay: 140ms">
            <div class="grid gap-4">
              <div class="glow-hover rounded-[28px] bg-[rgba(25,16,13,0.84)] p-5 text-white shadow-[0_22px_60px_rgba(18,12,10,0.22)]">
                <div class="text-xs font-semibold uppercase tracking-[0.22em] text-[#d7c16b]">RAG Flow</div>
                <p class="mt-3 text-lg font-semibold leading-8">
                  检索召回 → 相关性重排 → 回答生成 → 来源片段核验
                </p>
              </div>
              <div class="glow-hover rounded-[28px] border border-[rgba(118,82,59,0.14)] bg-white/88 p-5">
                <div class="text-sm font-semibold text-[rgba(74,54,43,0.72)]">为什么采用专业学习主视觉</div>
                <ul class="mt-3 space-y-3 text-sm leading-7 text-[rgba(64,46,38,0.82)]">
                  <li>把专业知识入口做成更明确、更具教学任务导向的首页。</li>
                  <li>用场景化空间隐喻知识组织、检索路径与来源回看。</li>
                  <li>让技术展示不脱离真实应用场景，而是落在 AI 专业学习支持上。</li>
                </ul>
              </div>
            </div>
          </aside>
        </section>
      </main>
    </LibraryBackdrop>

    <main class="mx-auto max-w-7xl space-y-8 px-6 pb-16 pt-10">
      <div class="scene-divider" />
      <section class="stagger-grid grid gap-5 lg:grid-cols-3">
        <article
          v-for="card in capabilityCards"
          :key="card.title"
          class="workspace-card glow-hover reveal-item rounded-[28px] p-6 transition duration-300 hover:-translate-y-1"
          v-reveal
        >
          <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-[rgba(174,92,63,0.12)] text-[#8b472f] shadow-sm">
            <i :class="card.icon" />
          </div>
          <h2 class="mt-5 text-xl font-semibold text-[#2f221f]">{{ card.title }}</h2>
          <p class="mt-3 text-sm leading-7 text-[rgba(76,58,49,0.78)]">{{ card.description }}</p>
        </article>
      </section>

      <section id="topic-grid" class="workspace-card reveal-item rounded-[32px] p-7" v-reveal>
        <div class="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Topic entry</p>
            <h2 class="mt-2 text-3xl font-black text-[#241917]">把首页变成 AI 专业知识入口</h2>
            <p class="mt-3 max-w-3xl text-sm leading-7 text-[rgba(76,58,49,0.78)]">
              不只是展示系统能力，也把人工智能专业学习最常见的问题组织成可以直接提问的入口。
            </p>
          </div>
          <button type="button" class="landing-secondary" @click="handlePrimaryAction">进入工作台</button>
        </div>

        <div class="stagger-grid mt-6 grid gap-5 lg:grid-cols-3">
          <article v-for="topic in topicCards" :key="topic.title" class="glow-hover magnetic-card reveal-item rounded-[28px] border border-[rgba(118,82,59,0.14)] bg-white/88 p-6 shadow-sm" v-reveal>
            <h3 class="text-xl font-semibold text-[#2f221f]">{{ topic.title }}</h3>
            <div class="mt-4 flex flex-wrap gap-2">
              <span v-for="point in topic.points" :key="point" class="landing-tag">{{ point }}</span>
            </div>
            <button type="button" class="landing-link mt-6" @click="openTopicPrompt(topic.prompt)">
              以此主题发起问答
              <i class="fa-solid fa-arrow-up-right-from-square" />
            </button>
          </article>
        </div>
      </section>

      <section class="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <article class="workspace-card reveal-item rounded-[32px] p-7" v-reveal>
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Answer design</p>
          <h2 class="mt-2 text-2xl font-black text-[#241917]">回答不是终点，来源核验才是产品信任感来源</h2>
          <div class="mt-5 grid gap-4 md:grid-cols-2">
            <div class="rounded-[24px] bg-[rgba(174,92,63,0.08)] p-5">
              <h3 class="font-semibold text-[#4d352c]">系统会尽量返回</h3>
              <ul class="mt-3 space-y-2 text-sm leading-7 text-[rgba(76,58,49,0.78)]">
                <li>来源片段与章节名称</li>
                <li>适合继续追问的专业主题</li>
                <li>便于评估效果的检索链路信息</li>
              </ul>
            </div>
            <div class="rounded-[24px] bg-[rgba(34,24,19,0.84)] p-5 text-white">
              <h3 class="font-semibold text-white">适合演示的问题</h3>
              <p class="mt-3 text-sm leading-7 text-[rgba(255,248,241,0.76)]">
                “请结合人工智能专业培养方案，说明课程体系、实践环节和毕业设计要求之间的关系。”
              </p>
            </div>
          </div>
        </article>

        <article class="workspace-card reveal-item rounded-[32px] p-7" v-reveal="120">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Entry options</p>
          <div class="mt-4 space-y-4 text-sm leading-7 text-[rgba(76,58,49,0.78)]">
            <p>未登录用户可以先体验公开 RAG 问答主链路；登录后再打开历史记录、知识空间与持续学习入口。</p>
            <p>如果你要展示系统能力，建议从首页搜索进入工作台；如果你要演示连续使用，则直接登录后进入工作台和历史页。</p>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<style scoped>
.landing-scene {
  border-bottom-left-radius: 36px;
  border-bottom-right-radius: 36px;
  box-shadow: 0 36px 96px rgba(53, 35, 26, 0.12);
}

.landing-copy {
  padding-top: 1.5rem;
}

.landing-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.68rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(126, 91, 67, 0.16);
  background: rgba(255, 251, 246, 0.78);
  color: #6e4a3a;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  box-shadow: 0 16px 40px rgba(73, 47, 35, 0.08);
}

.landing-title {
  margin-top: 1.5rem;
  color: #221816;
  font-size: clamp(3rem, 6vw, 5.6rem);
  font-weight: 900;
  line-height: 0.98;
  letter-spacing: -0.05em;
}

.landing-title span {
  display: block;
  color: #8b472f;
}

.landing-description {
  margin-top: 1.2rem;
  max-width: 52rem;
  color: rgba(73, 55, 46, 0.82);
  font-size: 1.05rem;
  line-height: 1.95;
}

.landing-actions,
.landing-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
}

.landing-primary,
.landing-secondary,
.landing-prompt,
.landing-link,
.landing-tag {
  transition: transform 180ms ease, box-shadow 180ms ease, background-color 180ms ease, color 180ms ease;
}

.landing-primary,
.landing-secondary,
.landing-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
}

.landing-primary {
  padding: 1rem 1.4rem;
  border-radius: 999px;
  color: #fff7f0;
  background: linear-gradient(135deg, #944b30 0%, #c68453 100%);
  box-shadow: 0 18px 40px rgba(148, 75, 48, 0.2);
  font-weight: 800;
}

.landing-secondary {
  padding: 1rem 1.3rem;
  border-radius: 999px;
  border: 1px solid rgba(126, 91, 67, 0.16);
  background: rgba(255, 251, 246, 0.74);
  color: #5c4439;
  font-weight: 700;
}

.landing-prompt {
  padding: 0.8rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(126, 91, 67, 0.14);
  background: rgba(255, 251, 246, 0.76);
  color: rgba(77, 54, 43, 0.86);
  font-size: 0.9rem;
  text-align: left;
  box-shadow: 0 14px 36px rgba(73, 47, 35, 0.06);
}

.landing-link {
  padding: 0;
  color: #8b472f;
  font-size: 0.92rem;
  font-weight: 800;
}

.landing-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.55rem 0.9rem;
  border-radius: 999px;
  background: rgba(174, 92, 63, 0.08);
  color: #6e4a3a;
  font-size: 0.82rem;
  font-weight: 700;
}

.landing-primary:hover,
.landing-secondary:hover,
.landing-prompt:hover,
.landing-link:hover {
  transform: translateY(-1px);
}

.landing-panel {
  align-self: end;
}

@media (max-width: 900px) {
  .landing-scene {
    border-bottom-left-radius: 28px;
    border-bottom-right-radius: 28px;
  }

  .landing-hero {
    min-height: auto;
    padding-top: 2rem;
  }
}
</style>
