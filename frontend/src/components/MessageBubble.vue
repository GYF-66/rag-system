<script setup lang="ts">
import { computed, ref } from 'vue';

import type { ChatMessage, KnowledgeChunk, GraphContext } from '@/types';
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
  co_required: '同期',
};

interface Props {
  message: ChatMessage;
  showActions?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showActions: true,
});

const hasPerspectives = computed(
  () =>
    props.message.role === 'assistant' &&
    Array.isArray(props.message.perspectives) &&
    props.message.perspectives.length > 0,
);

const hasThinking = computed(
  () => props.message.role === 'assistant' && !!props.message.thinkingProcess,
);

const graphContext = computed<GraphContext | null>(() => {
  if (props.message.role !== 'assistant') return null;
  return props.message.graphContext ?? null;
});

const graphExpanded = ref(false);

const copied = ref(false);

function formatTime(value?: string) {
  if (!value) return '';
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatScore(value?: number) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'n/a';
  }
  return value.toFixed(2);
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
    GraphRAG: '图谱RAG',
    CoT: 'CoT推理',
    SelfRAG: '自反思',
  };
  return mapping[label] ?? label;
}

const metadataPills = computed(() => {
  if (props.message.role !== 'assistant' || !props.message.metadata) {
    return [];
  }

  const metadata = props.message.metadata;
  const pills: Array<{ label: string; value: string }> = [];
  const retrievalMethod = metadata.retrieval_method;
  const sourceCount = metadata.source_count;
  const variantCount = metadata.retrieval_variant_count;
  const totalDuration = metadata.total_duration_ms;
  const adaptiveRoute = metadata.adaptive_route;
  const hydeUsed = metadata.hyde_used;
  const cragEval = metadata.crag_evaluation as { quality_score?: number } | undefined;

  if (typeof adaptiveRoute === 'string' && adaptiveRoute) {
    pills.push({ label: 'route', value: adaptiveRoute.toUpperCase() });
  }
  if (typeof retrievalMethod === 'string' && retrievalMethod) {
    pills.push({ label: 'retrieval', value: retrievalMethod });
  }
  if (typeof hydeUsed === 'boolean') {
    pills.push({ label: 'HyDE', value: hydeUsed ? '✓' : '✗' });
  }
  if (cragEval?.quality_score != null) {
    pills.push({ label: 'CRAG', value: cragEval.quality_score.toFixed(2) });
  }
  const graphRagUsed = metadata.graph_rag_used;
  if (typeof graphRagUsed === 'boolean') {
    pills.push({ label: 'GraphRAG', value: graphRagUsed ? '✓' : '✗' });
  }
  const cotUsed = metadata.cot_used;
  if (typeof cotUsed === 'boolean') {
    pills.push({ label: 'CoT', value: cotUsed ? '✓' : '✗' });
  }
  const selfRagReflection = metadata.self_rag_reflection;
  if (typeof selfRagReflection === 'string') {
    const reflectMap: Record<string, string> = { supported: '✓', partially_supported: '△', not_supported: '✗' };
    pills.push({ label: 'SelfRAG', value: reflectMap[selfRagReflection] ?? selfRagReflection });
  }

  if (typeof variantCount === 'number') {
    pills.push({ label: 'variants', value: String(variantCount) });
  }
  if (typeof sourceCount === 'number') {
    pills.push({ label: 'sources', value: String(sourceCount) });
  }
  const latency = formatLatency(totalDuration);
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
    v-memo="[message.content, message.createdAt, message.sources, message.metadata, copied]"
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
        message.role === 'user' ? 'bg-emerald-500' : 'bg-slate-800',
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
          'max-w-[82vw] rounded-3xl px-4 py-3 shadow-sm sm:max-w-[720px]',
          message.role === 'user'
            ? 'rounded-br-md bg-emerald-500 text-white'
            : 'rounded-bl-md border border-slate-200 bg-white text-slate-800',
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
        <MarkdownRenderer v-else :content="message.content" />

        <!-- Thinking Process Panel -->
        <ThinkingProcessPanel
          v-if="hasThinking"
          :process="message.thinkingProcess!"
          :metadata="message.metadata"
        />

        <!-- GraphRAG 知识图谱上下文面板 -->
        <div
          v-if="graphContext"
          class="mt-4 border-t border-slate-200 pt-3"
          data-testid="graph-context"
        >
          <button
            type="button"
            class="flex w-full items-center gap-2 text-left text-xs font-semibold text-blue-600 transition hover:text-blue-800"
            @click="graphExpanded = !graphExpanded"
          >
            <i :class="['fa-solid fa-chevron-right text-[10px] transition-transform', graphExpanded ? 'rotate-90' : '']" />
            <i class="fa-solid fa-diagram-project" />
            <span>知识图谱上下文</span>
            <span class="font-normal text-slate-400">
              {{ graphContext.node_count }} 节点 · {{ graphContext.edge_count }} 边
            </span>
          </button>

          <Transition name="graph-panel">
            <div v-if="graphExpanded" class="mt-3 space-y-3">
              <!-- 相关课程 -->
              <div v-if="graphContext.related_courses.length">
                <p class="mb-1.5 text-[11px] font-medium tracking-wider text-slate-500">相关课程</p>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="course in graphContext.related_courses"
                    :key="course.code"
                    class="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700"
                  >
                    <i class="fa-solid fa-book text-[9px]" />
                    {{ course.name }}
                    <span v-if="course.semester" class="text-blue-400">S{{ course.semester }}</span>
                  </span>
                </div>
              </div>

              <!-- 相关知识点 -->
              <div v-if="graphContext.related_concepts.length">
                <p class="mb-1.5 text-[11px] font-medium tracking-wider text-slate-500">相关知识点</p>
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="concept in graphContext.related_concepts"
                    :key="concept"
                    class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700"
                  >
                    {{ concept }}
                  </span>
                </div>
              </div>

              <!-- 关系链路 -->
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

        <div v-if="metadataPills.length" class="mt-4 flex flex-wrap gap-2 border-t border-slate-200 pt-3" data-testid="metadata-pills">
          <span
            v-for="pill in metadataPills"
            :key="`${pill.label}-${pill.value}`"
            class="rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-medium tracking-[0.08em] text-white"
          >
            {{ toMetadataLabel(pill.label) }}: {{ pill.value }}
          </span>
        </div>

        <div
          v-if="displaySources.length && !hasPerspectives"
          class="mt-4 space-y-3 border-t border-slate-200 pt-3"
          data-testid="source-block"
        >
          <div class="flex items-center justify-between gap-3">
            <p class="text-xs font-semibold tracking-[0.16em] text-slate-500">引用片段</p>
            <span class="text-[11px] text-slate-400">{{ displaySources.length }} 条参考片段</span>
          </div>

          <article
            v-for="(source, index) in displaySources"
            :key="`${source.id}-${index}`"
            class="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600"
            data-testid="source-card"
          >
            <div class="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
              <span class="rounded-full bg-white px-2 py-0.5 font-semibold text-slate-600">#{{ index + 1 }}</span>
              <span v-if="source.title" class="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700" :title="source.source_path">
                <i class="fa-solid fa-file-lines mr-1" />{{ source.title }}
              </span>
              <span v-if="source.section" class="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                <i class="fa-solid fa-bookmark mr-1" />{{ source.section }}
              </span>
              <span class="rounded-full bg-white px-2 py-0.5">相关度 {{ formatScore(source.similarity) }}</span>
              <span class="rounded-full bg-white px-2 py-0.5">重排 {{ formatScore(source.rerank_score) }}</span>
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
