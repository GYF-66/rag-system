<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import type { ChatMessage, ChatMetadata, GraphContext, KnowledgeChunk, ThinkingProcess } from '@/types';
import { formatSourceSnippet } from '@/utils/ragFormatting';
import MarkdownRenderer from './MarkdownRenderer.vue';
import PerspectiveTabs from './PerspectiveTabs.vue';
import ThinkingProcessPanel from './ThinkingProcess.vue';

const EDGE_TYPE_LABELS: Record<string, string> = {
  prerequisite: '先修',
  leads_to: '后续',
  contains: '包含',
  supports: '支撑',
  related: '关联',
  co_required: '同修',
};

interface Props {
  message: ChatMessage;
  showActions?: boolean;
}

interface MetaPill {
  label: string;
  value: string;
  interactive?: boolean;
  testId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  showActions: true,
});

const hasPerspectives = computed(
  () =>
    props.message.role === 'assistant'
    && Array.isArray(props.message.perspectives)
    && props.message.perspectives.length > 0,
);

const graphContext = computed<GraphContext | null>(() => {
  if (props.message.role !== 'assistant') return null;
  return props.message.graphContext ?? null;
});

const metadata = computed<ChatMetadata>(() => props.message.metadata ?? {});

const graphExpanded = ref(false);
const thinkingExpanded = ref(false);
const thinkingPanelRef = ref<HTMLElement | null>(null);
const copied = ref(false);

const thinkingProcessForRender = computed<Partial<ThinkingProcess>>(
  () => props.message.thinkingProcess ?? props.message.thinkingProcessDraft ?? {},
);

const hasThinkingPanel = computed(
  () =>
    props.message.role === 'assistant'
    && (
      !!props.message.thinkingProcess
      || !!props.message.thinkingProcessDraft
      || props.message.streamStatus === 'streaming'
      || props.message.streamStatus === 'error'
      || !!metadata.value.cot_used
      || !!metadata.value.crag_evaluation
      || !!metadata.value.self_rag
    ),
);

watch(
  () => props.message.streamStatus,
  (status) => {
    if (status === 'streaming' && hasThinkingPanel.value) {
      thinkingExpanded.value = true;
    }
  },
  { immediate: true },
);

function formatTime(value?: string) {
  if (!value) return '';
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatScore(value?: number | null) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'n/a';
  }
  return value.toFixed(2);
}

function formatPercent(value: unknown) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '等待校验';
  }
  return `${Math.round(value * 100)}%`;
}

function formatLatency(value: unknown) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return null;
  }
  return `${Math.round(value)} ms`;
}

function toMetadataLabel(label: string) {
  const mapping: Record<string, string> = {
    retrieval: '检索',
    variants: '变体',
    sources: '来源',
    latency: '耗时',
    route: '路由',
    HyDE: 'HyDE',
    CRAG: 'CRAG',
    GraphRAG: 'GraphRAG',
    CoT: '思考',
    SelfRAG: 'Self-RAG',
  };
  return mapping[label] ?? label;
}

const metadataPills = computed<MetaPill[]>(() => {
  if (props.message.role !== 'assistant') {
    return [];
  }

  const pills: MetaPill[] = [];
  const cragEval = metadata.value.crag_evaluation;
  const selfRag = metadata.value.self_rag;

  if (typeof metadata.value.adaptive_route === 'string' && metadata.value.adaptive_route) {
    pills.push({ label: 'route', value: metadata.value.adaptive_route.toUpperCase() });
  }

  if (typeof metadata.value.retrieval_method === 'string' && metadata.value.retrieval_method) {
    pills.push({ label: 'retrieval', value: metadata.value.retrieval_method });
  }

  if (typeof metadata.value.hyde_used === 'boolean') {
    pills.push({ label: 'HyDE', value: metadata.value.hyde_used ? '已启用' : '未启用' });
  }

  if (cragEval) {
    pills.push({
      label: 'CRAG',
      value: typeof cragEval.quality_score === 'number'
        ? `${formatScore(cragEval.quality_score)} · ${cragEval.action ?? 'accept'}`
        : '评估中',
      interactive: hasThinkingPanel.value,
      testId: 'crag-pill',
    });
  }

  if (typeof metadata.value.graph_rag_used === 'boolean') {
    pills.push({ label: 'GraphRAG', value: metadata.value.graph_rag_used ? '已启用' : '未启用' });
  }

  if (typeof metadata.value.cot_used === 'boolean') {
    pills.push({
      label: 'CoT',
      value: metadata.value.cot_used ? '查看思考' : '未启用',
      interactive: hasThinkingPanel.value,
      testId: 'thinking-pill',
    });
  }

  if (selfRag) {
    pills.push({
      label: 'SelfRAG',
      value: selfRag.status && selfRag.status !== 'waiting'
        ? `${formatPercent(selfRag.confidence)} · ${selfRag.status}`
        : '等待校验',
      interactive: hasThinkingPanel.value,
      testId: 'self-rag-pill',
    });
  } else if (typeof metadata.value.self_rag_reflection === 'string') {
    pills.push({
      label: 'SelfRAG',
      value: metadata.value.self_rag_reflection,
      interactive: hasThinkingPanel.value,
      testId: 'self-rag-pill',
    });
  }

  if (typeof metadata.value.retrieval_variant_count === 'number') {
    pills.push({ label: 'variants', value: String(metadata.value.retrieval_variant_count) });
  }

  if (typeof metadata.value.source_count === 'number') {
    pills.push({ label: 'sources', value: String(metadata.value.source_count) });
  }

  const latency = formatLatency(metadata.value.total_duration_ms);
  if (latency) {
    pills.push({ label: 'latency', value: latency });
  }

  return pills;
});

const displaySources = computed<Array<KnowledgeChunk & { displayText: string }>>(() =>
  (props.message.sources ?? []).map((source) => ({
    ...source,
    displayText: formatSourceSnippet(source.text),
  })),
);

const bubbleTestId = computed(() =>
  props.message.role === 'assistant' ? 'answer-block' : 'message-bubble',
);

function pillDisplayValue(pill: MetaPill) {
  if (pill.label !== 'CoT') {
    return pill.value;
  }

  if (!hasThinkingPanel.value) {
    return pill.value;
  }

  return thinkingExpanded.value ? '已展开' : '查看思考';
}

async function toggleThinkingPanel() {
  if (!hasThinkingPanel.value) {
    return;
  }

  thinkingExpanded.value = !thinkingExpanded.value;

  if (thinkingExpanded.value) {
    await nextTick();
    if (typeof thinkingPanelRef.value?.scrollIntoView === 'function') {
      thinkingPanelRef.value.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

async function copyContent() {
  const text = props.message.content;

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', 'true');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }

    copied.value = true;
    window.setTimeout(() => {
      copied.value = false;
    }, 2000);
  } catch {
    copied.value = false;
  }
}
</script>

<template>
  <div
    v-memo="[message.content, message.createdAt, message.sources, message.metadata, message.thinkingProcess, message.thinkingProcessDraft, message.streamStatus, copied, thinkingExpanded]"
    :class="[
      'group flex gap-3',
      message.role === 'user' ? 'flex-row-reverse' : 'flex-row',
    ]"
    data-testid="message-row"
    :data-role="message.role"
  >
    <div
      :class="[
        'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-2xl shadow-sm sm:h-10 sm:w-10',
        message.role === 'user' ? 'bg-[#a35d52]' : 'bg-[#2f231f]',
      ]"
    >
      <i
        :class="[
          'fa-solid text-sm text-white sm:text-base',
          message.role === 'user' ? 'fa-user' : 'fa-robot',
        ]"
      />
    </div>

    <div class="flex flex-col gap-2" :class="message.role === 'user' ? 'items-end' : 'items-start'">
      <div
        :class="[
          'max-w-[82vw] rounded-3xl px-4 py-3 shadow-sm sm:max-w-[760px]',
          message.role === 'user'
            ? 'rounded-br-md bg-[#a35d52] text-white'
            : 'rounded-bl-md border border-[rgba(120,85,63,0.14)] bg-[rgba(255,252,248,0.96)] text-slate-800',
        ]"
        :data-testid="bubbleTestId"
      >
        <p v-if="message.role === 'user'" class="whitespace-pre-wrap text-sm leading-relaxed sm:text-[15px]">
          {{ message.content }}
        </p>

        <PerspectiveTabs
          v-else-if="hasPerspectives"
          :perspectives="message.perspectives!"
          :sources="message.sources"
        />

        <div v-else>
          <div v-if="message.content" class="min-h-[1.75rem]">
            <MarkdownRenderer :content="message.content" typewriter />
          </div>
          <div
            v-else-if="message.streaming || message.streamStatus === 'streaming'"
            class="rounded-2xl border border-dashed border-[rgba(148,75,48,0.22)] bg-[rgba(250,244,236,0.8)] px-4 py-3 text-sm text-[rgba(82,60,50,0.82)]"
            data-testid="answer-placeholder"
          >
            正在整理回答，请稍候…
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500"
            data-testid="answer-placeholder"
          >
            当前回答内容暂未生成。
          </div>

          <span
            v-if="message.streaming"
            class="ml-1 inline-block h-4 w-2 animate-pulse rounded-sm bg-[#a35d52] align-middle"
            data-testid="streaming-cursor"
          />
        </div>

        <div v-if="hasThinkingPanel" ref="thinkingPanelRef" class="mt-4">
          <ThinkingProcessPanel
            :process="thinkingProcessForRender"
            :metadata="message.metadata"
            :stream-status="message.streamStatus"
            :step-statuses="message.thinkingStatusMap"
            :expanded="thinkingExpanded"
            :answer-content="message.content"
            @update:expanded="thinkingExpanded = $event"
          />
        </div>

        <div
          v-if="graphContext"
          class="mt-4 rounded-3xl border border-[rgba(120,85,63,0.12)] bg-white/85 p-4"
          data-testid="graph-context"
        >
          <button
            type="button"
            class="flex w-full items-center gap-2 text-left text-xs font-semibold text-[#8b472f] transition hover:text-[#6f3625]"
            @click="graphExpanded = !graphExpanded"
          >
            <i :class="['fa-solid fa-chevron-right text-[10px] transition-transform', graphExpanded ? 'rotate-90' : '']" />
            <i class="fa-solid fa-diagram-project" />
            <span>知识图谱上下文</span>
            <span class="font-normal text-slate-400">
              {{ graphContext.node_count }} 节点 · {{ graphContext.edge_count }} 关系
            </span>
          </button>

          <Transition name="graph-panel">
            <div v-if="graphExpanded" class="mt-3 space-y-3">
              <div v-if="graphContext.related_courses.length">
                <p class="mb-1.5 text-[11px] font-medium tracking-wider text-slate-500">相关课程</p>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="course in graphContext.related_courses"
                    :key="course.code"
                    class="inline-flex items-center gap-1 rounded-full bg-[#f7efe7] px-2.5 py-1 text-[11px] font-medium text-[#8b472f]"
                  >
                    <i class="fa-solid fa-book text-[9px]" />
                    {{ course.name }}
                    <span v-if="course.semester" class="text-[#c68453]">S{{ course.semester }}</span>
                  </span>
                </div>
              </div>

              <div v-if="graphContext.related_concepts.length">
                <p class="mb-1.5 text-[11px] font-medium tracking-wider text-slate-500">相关知识点</p>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="concept in graphContext.related_concepts"
                    :key="concept"
                    class="rounded-full bg-[#f3f0ea] px-2 py-0.5 text-[11px] text-[#5a4a42]"
                  >
                    {{ concept }}
                  </span>
                </div>
              </div>

              <div v-if="graphContext.relationships.length">
                <p class="mb-1.5 text-[11px] font-medium tracking-wider text-slate-500">知识关系</p>
                <div class="space-y-1">
                  <div
                    v-for="(rel, ri) in graphContext.relationships"
                    :key="ri"
                    class="flex items-center gap-1.5 text-[11px] text-slate-600"
                  >
                    <span class="font-medium">{{ rel.source }}</span>
                    <span class="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500">
                      {{ EDGE_TYPE_LABELS[rel.type] || rel.type }}
                    </span>
                    <i class="fa-solid fa-arrow-right text-[8px] text-slate-400" />
                    <span class="font-medium">{{ rel.target }}</span>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <div
          v-if="metadataPills.length"
          class="mt-4 flex flex-wrap gap-2 border-t border-[rgba(120,85,63,0.12)] pt-3"
          data-testid="metadata-pills"
        >
          <component
            v-for="pill in metadataPills"
            :key="`${pill.label}-${pill.value}`"
            :is="pill.interactive ? 'button' : 'span'"
            :type="pill.interactive ? 'button' : undefined"
            :disabled="pill.interactive && !hasThinkingPanel"
            :data-testid="pill.testId"
            :aria-expanded="pill.interactive && hasThinkingPanel ? String(thinkingExpanded) : undefined"
            class="rounded-full bg-[#2f231f] px-2.5 py-1 text-[11px] font-medium tracking-[0.08em] text-white"
            :class="pill.interactive ? 'cursor-pointer transition hover:bg-[#4a3830] disabled:cursor-not-allowed disabled:bg-slate-500' : ''"
            @click="pill.interactive ? toggleThinkingPanel() : undefined"
          >
            {{ toMetadataLabel(pill.label) }}: {{ pillDisplayValue(pill) }}
          </component>
        </div>

        <div
          v-if="displaySources.length && !hasPerspectives"
          class="mt-4 space-y-3 border-t border-[rgba(120,85,63,0.12)] pt-3"
          data-testid="source-block"
        >
          <div class="flex items-center justify-between gap-3">
            <p class="text-xs font-semibold tracking-[0.16em] text-slate-500">引用片段</p>
            <span class="text-[11px] text-slate-400">{{ displaySources.length }} 条参考片段</span>
          </div>

          <article
            v-for="(source, index) in displaySources"
            :key="`${source.id}-${index}`"
            class="rounded-2xl border border-[rgba(120,85,63,0.12)] bg-white/90 px-3 py-3 text-sm text-slate-600"
            data-testid="source-card"
          >
            <div class="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
              <span class="rounded-full bg-slate-100 px-2 py-0.5 font-semibold text-slate-600">#{{ index + 1 }}</span>
              <span v-if="source.title" class="rounded-full bg-[#f7efe7] px-2 py-0.5 text-[#8b472f]" :title="source.source_path">
                <i class="fa-solid fa-file-lines mr-1" />{{ source.title }}
              </span>
              <span v-if="source.section" class="rounded-full bg-[#edf5ef] px-2 py-0.5 text-emerald-700">
                <i class="fa-solid fa-bookmark mr-1" />{{ source.section }}
              </span>
              <span class="rounded-full bg-slate-100 px-2 py-0.5">相关度 {{ formatScore(source.similarity) }}</span>
              <span class="rounded-full bg-slate-100 px-2 py-0.5">重排 {{ formatScore(source.rerank_score) }}</span>
            </div>
            <p
              class="mt-3 whitespace-pre-line leading-7 text-slate-700"
              data-testid="source-snippet"
            >{{ source.displayText }}</p>
          </article>
        </div>
      </div>

      <div class="flex items-center gap-2 px-1 text-xs text-slate-400">
        <span v-if="message.createdAt">{{ formatTime(message.createdAt) }}</span>
        <button
          v-if="showActions && message.role === 'assistant'"
          type="button"
          class="rounded-full px-2 py-1 transition hover:bg-slate-100 hover:text-slate-600"
          data-testid="copy-answer"
          @click="copyContent"
        >
          {{ copied ? '已复制' : '复制' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.graph-panel-enter-active {
  transition: all 0.25s ease-out;
}

.graph-panel-leave-active {
  transition: all 0.15s ease-in;
}

.graph-panel-enter-from,
.graph-panel-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-4px);
}

.graph-panel-enter-to,
.graph-panel-leave-from {
  opacity: 1;
  max-height: 600px;
}
</style>
