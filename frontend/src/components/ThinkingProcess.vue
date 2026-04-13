<script setup lang="ts">
import { computed, ref } from 'vue';

import type {
  ChatMetadata,
  CragEvaluation,
  ReflectionResult,
  SelfRagMetadata,
  ThinkingProcess,
  ThinkingStepKey,
  ThinkingStepRunStatus,
  ThinkingStepStatusMap,
  ThinkingStepSummary,
} from '@/types';

interface Props {
  process: Partial<ThinkingProcess>;
  metadata?: ChatMetadata;
  streamStatus?: 'idle' | 'streaming' | 'done' | 'error';
  stepStatuses?: ThinkingStepStatusMap;
  expanded?: boolean;
  answerContent?: string;
}

type TraceStep = ThinkingStepSummary & {
  key: ThinkingStepKey;
  icon: string;
  label: string;
  runStatus: ThinkingStepRunStatus;
};

const props = defineProps<Props>();
const emit = defineEmits<{ (event: 'update:expanded', value: boolean): void }>();

const internalExpanded = ref(false);

const panelExpanded = computed(() =>
  props.expanded !== undefined ? props.expanded : internalExpanded.value,
);

function setExpanded(value: boolean) {
  if (props.expanded === undefined) {
    internalExpanded.value = value;
  }
  emit('update:expanded', value);
}

const STEP_META: Record<ThinkingStepKey, { icon: string; label: string; description: string }> = {
  query_analysis: { icon: 'fa-compass', label: '问题理解', description: '规范化问题、识别意图，并整理检索关键词。' },
  retrieval: { icon: 'fa-book-open-reader', label: '证据检索', description: '执行检索召回，准备候选来源片段。' },
  reranking: { icon: 'fa-layer-group', label: '上下文整理', description: '对来源片段进行去重、重排和质量判断。' },
  reasoning: { icon: 'fa-pen-nib', label: '回答生成', description: '依据证据组织回答，并持续流式输出正文。' },
  reflection: { icon: 'fa-shield-halved', label: 'Self-RAG 校验', description: '对答案与证据进行一致性检查，必要时修订。' },
};

function formatScore(value?: number | null) {
  return typeof value === 'number' && !Number.isNaN(value) ? value.toFixed(2) : '待更新';
}

function formatPercent(value?: number | null) {
  return typeof value === 'number' && !Number.isNaN(value) ? `${Math.round(value * 100)}%` : '等待校验';
}

function formatDuration(value?: number | null) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '';
  return value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${Math.round(value)}ms`;
}

function statusLabel(status?: string | null) {
  const mapping: Record<string, string> = {
    waiting: '等待校验',
    supported: '证据支持',
    partially_supported: '部分支持',
    not_supported: '证据不足',
    skipped: '已跳过',
  };
  return status ? (mapping[status] ?? status) : '等待校验';
}

function asStringArray(value: unknown) {
  return Array.isArray(value)
    ? value.map((item) => (typeof item === 'string' ? item.trim() : '')).filter(Boolean)
    : [];
}

function runStatusMeta(status: ThinkingStepRunStatus) {
  const mapping: Record<ThinkingStepRunStatus, { text: string; cls: string; dot: string }> = {
    waiting: { text: '等待中', cls: 'bg-slate-100 text-slate-600', dot: 'bg-slate-300' },
    streaming: { text: '进行中', cls: 'bg-blue-100 text-blue-700', dot: 'bg-blue-500' },
    done: { text: '已完成', cls: 'bg-emerald-100 text-emerald-700', dot: 'bg-emerald-500' },
    warning: { text: '需关注', cls: 'bg-amber-100 text-amber-700', dot: 'bg-amber-500' },
  };
  return mapping[status];
}

function buildMetrics(step: ThinkingStepSummary) {
  const output = (step.output_data ?? {}) as Record<string, unknown>;
  const metrics: Array<{ label: string; value: string }> = [];
  if (typeof output.retrieved_count === 'number') metrics.push({ label: '召回', value: `${output.retrieved_count} 条` });
  if (typeof output.final_count === 'number') metrics.push({ label: '保留', value: `${output.final_count} 条` });
  if (typeof output.crag_score === 'number') metrics.push({ label: 'CRAG', value: formatScore(output.crag_score) });
  if (typeof output.status === 'string') metrics.push({ label: '状态', value: statusLabel(output.status) });
  if (typeof output.confidence === 'number') metrics.push({ label: '置信度', value: formatPercent(output.confidence) });
  return metrics;
}

function buildPlaceholderStep(key: ThinkingStepKey, runStatus: ThinkingStepRunStatus): ThinkingStepSummary {
  const meta = STEP_META[key];
  const waitingReasoning: Record<ThinkingStepKey, string> = {
    query_analysis: '等待接收问题分析结果。',
    retrieval: '等待检索来源片段。',
    reranking: '等待重排与质量判断结果。',
    reasoning: props.streamStatus === 'streaming' ? '正在流式输出回答。' : '等待生成回答正文。',
    reflection: '等待 Self-RAG 校验返回。',
  };

  return {
    step_name: meta.label,
    description: meta.description,
    reasoning: runStatus === 'done'
      ? `${meta.label}已完成，可展开查看细节。`
      : waitingReasoning[key],
  };
}

const routeInfo = computed(() => {
  const route = props.metadata?.adaptive_route;
  const mapping: Record<string, string> = {
    simple: '简单直检',
    standard: '标准链路',
    complex: '完整链路',
  };
  return typeof route === 'string' ? (mapping[route] ?? route.toUpperCase()) : '';
});

const queryRewrite = computed(() => props.metadata?.query_rewrite);
const crag = computed<CragEvaluation | null>(() => props.metadata?.crag_evaluation ?? null);
const selfRag = computed<SelfRagMetadata | null>(() => props.metadata?.self_rag ?? null);
const reflectionResult = computed<ReflectionResult | null>(() => props.process.reflection_result ?? null);

const statusMap = computed<ThinkingStepStatusMap>(() => {
  const defaults: ThinkingStepStatusMap = {
    query_analysis: props.process.query_analysis || props.metadata?.query_rewrite ? 'done' : 'waiting',
    retrieval: props.process.retrieval || typeof props.metadata?.source_count === 'number' ? 'done' : 'waiting',
    reranking: props.process.reranking || !!props.metadata?.crag_evaluation ? 'done' : 'waiting',
    reasoning: props.streamStatus === 'streaming'
      ? 'streaming'
      : props.process.reasoning || (props.answerContent ?? '').trim()
        ? 'done'
        : 'waiting',
    reflection: props.process.reflection || reflectionResult.value || (selfRag.value?.status && selfRag.value.status !== 'waiting')
      ? 'done'
      : 'waiting',
  };

  if (props.streamStatus === 'error') {
    defaults.reasoning = 'warning';
  }

  return {
    ...defaults,
    ...(props.stepStatuses ?? {}),
  };
});

const traceSteps = computed<TraceStep[]>(() => {
  const keys: ThinkingStepKey[] = ['query_analysis', 'retrieval', 'reranking', 'reasoning', 'reflection'];

  return keys.flatMap((key) => {
    const runStatus = statusMap.value[key] ?? 'waiting';
    const step = props.process[key] ?? buildPlaceholderStep(key, runStatus);

    if (
      runStatus === 'waiting'
      && !props.process[key]
      && key !== 'reflection'
      && !props.metadata
      && !props.answerContent
      && props.streamStatus !== 'streaming'
    ) {
      return [];
    }

    return [{
      key,
      icon: STEP_META[key].icon,
      label: STEP_META[key].label,
      runStatus,
      ...step,
    }];
  });
});

const currentStep = computed(() =>
  traceSteps.value.find((item) => item.runStatus === 'streaming')
  || [...traceSteps.value].reverse().find((item) => item.runStatus === 'warning')
  || [...traceSteps.value].reverse().find((item) => item.runStatus === 'done')
  || traceSteps.value[0]
  || null,
);

const reflectionBadge = computed(() => {
  const status = reflectionResult.value?.status ?? selfRag.value?.status;
  if (!status || status === 'waiting' || status === 'skipped') return '';
  return statusLabel(status);
});

const reflectionIssues = computed(() => reflectionResult.value?.issues ?? []);

const cragMetrics = computed(() => {
  const details = crag.value?.details ?? {};
  return [
    { key: 'similarity', label: 'similarity', value: details.similarity },
    { key: 'keyword_coverage', label: 'keyword_coverage', value: details.keyword_coverage },
    { key: 'diversity', label: 'diversity', value: details.diversity },
    { key: 'completeness', label: 'completeness', value: details.completeness },
  ];
});

const cragThresholdLow = computed(() => crag.value?.thresholds?.low ?? 0.3);
const cragThresholdHigh = computed(() => crag.value?.thresholds?.high ?? 0.6);
const cragHints = computed(() => asStringArray(crag.value?.correction_hints));
const cragActionsTaken = computed(() => asStringArray(crag.value?.correction?.actions_taken));

const selfRagStatus = computed(() => selfRag.value?.status ?? reflectionResult.value?.status ?? 'waiting');
const selfRagConfidence = computed(() => selfRag.value?.confidence ?? reflectionResult.value?.confidence ?? null);
const selfRagEvidenceCount = computed(() => selfRag.value?.evidence_count ?? Math.min(props.metadata?.source_count ?? 0, 5));

const answerSummary = computed(() => {
  const text = (props.answerContent ?? '').trim();
  if (!text) return '等待回答生成';
  return text.length > 120 ? `${text.slice(0, 120)}…` : text;
});

const summaryText = computed(() => {
  if (props.process.summary) return props.process.summary;
  if (!currentStep.value) return '等待生成思考过程。';
  return currentStep.value.runStatus === 'streaming'
    ? `${currentStep.value.label}正在更新中。`
    : '可展开查看当前问答链路的详细技术方法。';
});
</script>

<template>
  <div class="typewriter-pane overflow-hidden rounded-3xl border border-[rgba(120,85,63,0.14)] bg-white shadow-sm" data-testid="thinking-process">
    <button
      type="button"
      class="flex w-full items-start justify-between gap-4 px-4 py-4 text-left transition-colors hover:bg-slate-50"
      data-testid="thinking-process-toggle"
      @click="setExpanded(!panelExpanded)"
    >
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <span class="inline-flex items-center gap-2 rounded-full bg-[#2f231f] px-3 py-1 text-[11px] font-semibold tracking-[0.16em] text-white">
            <i class="fa-solid fa-terminal text-[10px]" />
            思考过程
          </span>
          <span v-if="routeInfo" class="rounded-full bg-blue-100 px-2.5 py-1 text-[11px] font-semibold text-blue-700">{{ routeInfo }}</span>
          <span
            v-if="currentStep"
            :class="[runStatusMeta(currentStep.runStatus).cls, 'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold']"
            data-testid="trace-status"
          >
            <span :class="[runStatusMeta(currentStep.runStatus).dot, 'h-1.5 w-1.5 rounded-full']" />
            {{ runStatusMeta(currentStep.runStatus).text }}
          </span>
          <span v-if="reflectionBadge" class="rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold text-emerald-700" data-testid="verification-badge">
            {{ reflectionBadge }}
          </span>
          <span v-if="process.total_duration_ms" class="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
            {{ formatDuration(process.total_duration_ms) }}
          </span>
        </div>

        <p class="mt-3 text-sm leading-6 text-slate-600">{{ summaryText }}</p>

        <div v-if="traceSteps.length" class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="step in traceSteps"
            :key="step.key"
            class="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600"
          >
            {{ step.label }}
          </span>
        </div>
      </div>

      <div class="flex items-center gap-2 pt-1 text-xs text-slate-400">
        <span>{{ panelExpanded ? '收起' : '展开' }}</span>
        <i :class="['fa-solid fa-chevron-down transition-transform', panelExpanded ? 'rotate-180' : '']" />
      </div>
    </button>

    <transition name="trace-panel">
      <div v-show="panelExpanded" class="space-y-4 border-t border-slate-200 px-4 py-4">
        <details
          v-for="step in traceSteps"
          :key="step.key"
          :open="step.runStatus === 'streaming'"
          class="trace-details rounded-2xl border border-slate-200 bg-slate-50"
        >
          <summary class="cursor-pointer list-none px-4 py-3">
            <div class="flex items-start gap-3">
              <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl bg-white shadow-sm">
                <i :class="['fa-solid', step.icon, 'text-slate-700']" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-sm font-semibold text-slate-900">{{ step.label }}</span>
                  <span :class="[runStatusMeta(step.runStatus).cls, 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium']">
                    <span :class="[runStatusMeta(step.runStatus).dot, 'h-1.5 w-1.5 rounded-full']" />
                    {{ runStatusMeta(step.runStatus).text }}
                  </span>
                  <span v-if="step.duration_ms" class="text-[11px] text-slate-400">{{ formatDuration(step.duration_ms) }}</span>
                </div>
                <p class="mt-1 text-sm leading-6 text-slate-600">{{ step.description || '展开查看当前步骤详情。' }}</p>
              </div>
              <i class="trace-chevron fa-solid fa-chevron-down mt-1 text-xs text-slate-400" />
            </div>
          </summary>
          <div class="space-y-3 border-t border-slate-200 px-4 py-4">
            <p v-if="step.reasoning" class="whitespace-pre-line rounded-2xl bg-white px-3 py-3 text-sm leading-6 text-slate-700">
              {{ step.reasoning }}
            </p>
            <div v-if="buildMetrics(step).length" class="flex flex-wrap gap-2">
              <span
                v-for="metric in buildMetrics(step)"
                :key="`${step.key}-${metric.label}`"
                class="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600"
              >
                {{ metric.label }}: <span class="font-semibold text-slate-800">{{ metric.value }}</span>
              </span>
            </div>
          </div>
        </details>

        <section class="grid gap-4 lg:grid-cols-2" data-testid="thinking-sidebar">
          <details class="trace-details rounded-2xl border border-slate-200 bg-white shadow-sm" data-testid="crag-method-card">
            <summary class="cursor-pointer list-none px-4 py-3">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-slate-900">CRAG 技术方法</p>
                  <p class="mt-1 text-sm text-slate-500">
                    {{ typeof crag?.quality_score === 'number' ? `CRAG ${formatScore(crag.quality_score)} · ${crag.action ?? 'accept'}` : 'CRAG 评估中' }}
                  </p>
                </div>
                <i class="trace-chevron fa-solid fa-chevron-down text-xs text-slate-400" />
              </div>
            </summary>
            <div class="space-y-4 border-t border-slate-100 px-4 py-4">
              <div class="rounded-2xl bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">计算公式</p>
                <p class="mt-2">0.35 similarity + 0.30 keyword_coverage + 0.15 diversity + 0.20 completeness</p>
              </div>

              <div class="space-y-3">
                <div v-for="metric in cragMetrics" :key="metric.key" class="rounded-2xl bg-slate-50 px-3 py-3">
                  <div class="flex items-center justify-between gap-3 text-sm text-slate-700">
                    <span>{{ metric.label }}</span>
                    <span class="font-semibold">{{ formatScore(metric.value) }} / 1.00</span>
                  </div>
                  <div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      class="h-full rounded-full bg-[#2f231f]"
                      :style="{ width: `${Math.max(0, Math.min(100, Number(metric.value ?? 0) * 100))}%` }"
                      :data-testid="`crag-metric-${metric.key}`"
                    />
                  </div>
                </div>
              </div>

              <div class="rounded-2xl bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">阈值解释</p>
                <p class="mt-2">&gt;= {{ cragThresholdHigh }} accept</p>
                <p>{{ cragThresholdLow }} ~ {{ cragThresholdHigh }} refine</p>
                <p>&lt; {{ cragThresholdLow }} reject</p>
              </div>

              <div class="rounded-2xl bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">当前动作</p>
                <p class="mt-2">{{ crag?.action ?? 'waiting' }}</p>
                <div v-if="cragHints.length" class="mt-3 flex flex-wrap gap-2">
                  <span v-for="hint in cragHints" :key="hint" class="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-medium text-amber-700">{{ hint }}</span>
                </div>
                <div v-if="cragActionsTaken.length" class="mt-3 flex flex-wrap gap-2">
                  <span v-for="action in cragActionsTaken" :key="action" class="rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-medium text-emerald-700">{{ action }}</span>
                </div>
              </div>
            </div>
          </details>

          <details class="trace-details rounded-2xl border border-slate-200 bg-white shadow-sm" data-testid="self-rag-method-card">
            <summary class="cursor-pointer list-none px-4 py-3">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-slate-900">Self-RAG 技术方法</p>
                  <p class="mt-1 text-sm text-slate-500">
                    {{ selfRagStatus === 'waiting' ? '等待 Self-RAG 校验' : `${formatPercent(selfRagConfidence)} · ${selfRagStatus}` }}
                  </p>
                </div>
                <i class="trace-chevron fa-solid fa-chevron-down text-xs text-slate-400" />
              </div>
            </summary>
            <div class="space-y-4 border-t border-slate-100 px-4 py-4">
              <div class="rounded-2xl bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">校验输入</p>
                <p class="mt-2"><span class="font-semibold text-slate-900">用户问题：</span>{{ queryRewrite?.original_query || queryRewrite?.normalized_query || '等待问题分析' }}</p>
                <p><span class="font-semibold text-slate-900">当前回答摘要：</span>{{ answerSummary }}</p>
                <p><span class="font-semibold text-slate-900">参与核查的证据数量：</span>{{ selfRagEvidenceCount }}</p>
              </div>

              <div class="rounded-2xl bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">校验流程</p>
                <ol class="mt-2 space-y-1">
                  <li>读取问题</li>
                  <li>读取当前回答</li>
                  <li>读取前 5 条证据摘要</li>
                  <li>LLM 输出 status / confidence / issues</li>
                  <li>必要时生成修订版回答</li>
                </ol>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <div class="rounded-2xl bg-slate-50 px-3 py-3">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">当前状态</p>
                  <p class="mt-2 text-sm font-semibold text-slate-800" data-testid="self-rag-status">{{ statusLabel(selfRagStatus) }}</p>
                </div>
                <div class="rounded-2xl bg-slate-50 px-3 py-3">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">置信度</p>
                  <p class="mt-2 text-sm font-semibold text-slate-800">{{ formatPercent(selfRagConfidence) }}</p>
                </div>
              </div>

              <div class="rounded-2xl bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">修订结果</p>
                <p class="mt-2">{{ selfRag?.revision_applied || reflectionResult?.revision_applied ? '已按证据修订回答' : '本轮未触发修订' }}</p>
                <ul v-if="reflectionIssues.length" class="mt-3 space-y-2" data-testid="reflection-issues">
                  <li v-for="issue in reflectionIssues" :key="issue" class="rounded-2xl bg-rose-50 px-3 py-2 text-rose-700">{{ issue }}</li>
                </ul>
                <p v-else class="mt-3 text-slate-500">
                  {{ selfRagStatus === 'waiting' ? 'reflection 事件到达后会立即更新状态、置信度和问题列表。' : '当前未发现需要额外提示的问题。' }}
                </p>
              </div>
            </div>
          </details>
        </section>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.typewriter-pane {
  font-family: var(--font-mono);
}

.trace-panel-enter-active,
.trace-panel-leave-active {
  transition: all 0.24s ease;
  max-height: 2400px;
  overflow: hidden;
}

.trace-panel-enter-from,
.trace-panel-leave-to {
  max-height: 0;
  opacity: 0;
}

.trace-details summary::-webkit-details-marker {
  display: none;
}

.trace-details[open] .trace-chevron {
  transform: rotate(180deg);
}

.trace-chevron {
  transition: transform 0.2s ease;
}
</style>
