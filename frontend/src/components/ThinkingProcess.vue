<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ThinkingProcess, ReflectionResult } from '@/types';

interface Props {
  process: ThinkingProcess;
  metadata?: Record<string, unknown>;
}

const props = defineProps<Props>();
const expanded = ref(false);
const cotExpanded = ref(false);

const steps = computed(() => {
  const p = props.process;
  const list = [
    { key: 'query_analysis', icon: 'fa-magnifying-glass-chart', color: 'text-blue-500', bg: 'bg-blue-50', ...p.query_analysis },
    { key: 'retrieval', icon: 'fa-database', color: 'text-emerald-500', bg: 'bg-emerald-50', ...p.retrieval },
    { key: 'reranking', icon: 'fa-arrow-up-wide-short', color: 'text-amber-500', bg: 'bg-amber-50', ...p.reranking },
    { key: 'reasoning', icon: 'fa-brain', color: 'text-violet-500', bg: 'bg-violet-50', ...p.reasoning },
  ].filter((s) => s.step_name);
  // Self-RAG 反思步骤
  if (p.reflection?.step_name) {
    list.push({ key: 'reflection', icon: 'fa-shield-halved', color: 'text-rose-500', bg: 'bg-rose-50', ...p.reflection });
  }
  return list;
});

const reflectionResult = computed<ReflectionResult | null>(() => props.process.reflection_result ?? null);

const reflectionBadge = computed(() => {
  const r = reflectionResult.value;
  if (!r || r.status === 'skipped') return null;
  const map: Record<string, { label: string; color: string; bg: string; icon: string }> = {
    supported: { label: '已验证', color: 'text-green-700', bg: 'bg-green-100', icon: 'fa-circle-check' },
    partially_supported: { label: '部分验证', color: 'text-amber-700', bg: 'bg-amber-100', icon: 'fa-triangle-exclamation' },
    not_supported: { label: '待修正', color: 'text-red-700', bg: 'bg-red-100', icon: 'fa-circle-xmark' },
  };
  return map[r.status] ?? null;
});

const hasCotReasoning = computed(() => {
  const reasoning = props.process.reasoning?.reasoning;
  return reasoning && reasoning.length > 80;
});

const cotPreview = computed(() => {
  const reasoning = props.process.reasoning?.reasoning ?? '';
  if (reasoning.length <= 120) return reasoning;
  return reasoning.slice(0, 120) + '...';
});

const routeInfo = computed(() => {
  const m = props.metadata;
  if (!m) return null;
  const route = m.adaptive_route as string | undefined;
  if (!route) return null;
  const map: Record<string, { label: string; color: string; bg: string }> = {
    simple: { label: 'SIMPLE', color: 'text-green-700', bg: 'bg-green-100' },
    standard: { label: 'STANDARD', color: 'text-blue-700', bg: 'bg-blue-100' },
    complex: { label: 'COMPLEX', color: 'text-purple-700', bg: 'bg-purple-100' },
  };
  return map[route] || { label: route.toUpperCase(), color: 'text-slate-700', bg: 'bg-slate-100' };
});

const pipelineDetails = computed(() => {
  const m = props.metadata;
  if (!m) return [];
  const items: Array<{ label: string; value: string; icon: string }> = [];
  if (m.retrieval_method) items.push({ label: '检索', icon: 'fa-route', value: String(m.retrieval_method) });
  if (typeof m.hyde_used === 'boolean') items.push({ label: 'HyDE', icon: 'fa-wand-magic-sparkles', value: m.hyde_used ? '启用' : '未启用' });
  const crag = m.crag_evaluation as { quality_score?: number } | undefined;
  if (crag?.quality_score != null) items.push({ label: 'CRAG', icon: 'fa-check-double', value: `${crag.quality_score.toFixed(2)}` });
  if (typeof m.source_count === 'number') items.push({ label: '来源', icon: 'fa-file-lines', value: `${m.source_count} 片段` });
  if (typeof m.cot_used === 'boolean') items.push({ label: 'CoT', icon: 'fa-brain', value: m.cot_used ? '启用' : '未启用' });
  if (typeof m.self_rag_reflection === 'string') items.push({ label: '反思', icon: 'fa-shield-halved', value: m.self_rag_reflection });
  return items;
});

function formatDuration(ms?: number) {
  if (typeof ms !== 'number') return '';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}
</script>

<template>
  <div class="mt-3 rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white overflow-hidden">
    <!-- Header -->
    <button
      type="button"
      class="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left transition-colors hover:bg-slate-100"
      @click="expanded = !expanded"
    >
      <div class="flex items-center gap-2">
        <i class="fa-solid fa-lightbulb text-amber-500 text-sm" />
        <span class="text-xs font-semibold tracking-wide text-slate-600">思考过程</span>
        <span v-if="routeInfo" :class="[routeInfo.bg, routeInfo.color, 'rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider']">
          {{ routeInfo.label }}
        </span>
        <!-- Self-RAG 验证徽章 -->
        <span
          v-if="reflectionBadge"
          :class="[reflectionBadge.bg, reflectionBadge.color, 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold']"
        >
          <i :class="['fa-solid', reflectionBadge.icon, 'text-[9px]']" />
          {{ reflectionBadge.label }}
        </span>
        <span v-if="process.total_duration_ms" class="text-[10px] text-slate-400">
          {{ formatDuration(process.total_duration_ms) }}
        </span>
      </div>
      <i :class="['fa-solid fa-chevron-down text-[10px] text-slate-400 transition-transform', expanded ? 'rotate-180' : '']" />
    </button>

    <!-- Pipeline Quick View (always visible) -->
    <div v-if="pipelineDetails.length" class="flex flex-wrap gap-1.5 px-4 pb-2.5">
      <span
        v-for="item in pipelineDetails"
        :key="item.label"
        class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600"
      >
        <i :class="['fa-solid', item.icon, 'text-[9px] text-slate-400']" />
        {{ item.label }}: <strong class="font-semibold text-slate-800">{{ item.value }}</strong>
      </span>
    </div>

    <!-- Expanded Steps -->
    <transition name="slide">
      <div v-show="expanded" class="border-t border-slate-200 px-4 py-3 space-y-3">
        <div v-for="(step, idx) in steps" :key="step.key" class="flex gap-3">
          <!-- Timeline -->
          <div class="flex flex-col items-center">
            <div :class="[step.bg, 'flex h-7 w-7 items-center justify-center rounded-full']">
              <i :class="['fa-solid', step.icon, step.color, 'text-xs']" />
            </div>
            <div v-if="idx < steps.length - 1" class="w-px flex-1 bg-slate-200 my-1" />
          </div>
          <!-- Content -->
          <div class="flex-1 pb-1">
            <div class="flex items-center gap-2">
              <span class="text-xs font-semibold text-slate-700">{{ step.step_name }}</span>
              <span v-if="step.duration_ms" class="text-[10px] text-slate-400">{{ formatDuration(step.duration_ms) }}</span>
            </div>
            <!-- CoT reasoning: 可折叠长文本 -->
            <template v-if="step.key === 'reasoning' && hasCotReasoning">
              <p class="mt-0.5 text-xs leading-relaxed text-slate-500">
                {{ cotExpanded ? step.reasoning : cotPreview }}
              </p>
              <button
                type="button"
                class="mt-1 text-[10px] font-medium text-violet-500 hover:text-violet-700 transition"
                @click.stop="cotExpanded = !cotExpanded"
              >
                {{ cotExpanded ? '收起推理链' : '展开完整推理链' }}
              </button>
            </template>
            <p v-else class="mt-0.5 text-xs leading-relaxed text-slate-500">{{ step.reasoning }}</p>
          </div>
        </div>

        <!-- Self-RAG 反思详情 -->
        <div v-if="reflectionResult && reflectionResult.status !== 'skipped'" class="rounded-xl border px-3 py-2" :class="reflectionBadge ? [reflectionBadge.bg.replace('100','50')] : 'bg-slate-50'">
          <div class="flex items-center gap-2 mb-1">
            <i class="fa-solid fa-shield-halved text-xs" :class="reflectionBadge?.color ?? 'text-slate-500'" />
            <span class="text-[11px] font-semibold" :class="reflectionBadge?.color ?? 'text-slate-600'">Self-RAG 验证</span>
            <span class="text-[10px] text-slate-400">置信度 {{ (reflectionResult.confidence * 100).toFixed(0) }}%</span>
          </div>
          <div v-if="reflectionResult.issues.length" class="space-y-0.5">
            <p v-for="(issue, ii) in reflectionResult.issues" :key="ii" class="text-[11px] text-slate-600 pl-5">
              <i class="fa-solid fa-circle text-[4px] mr-1.5 align-middle text-slate-400" />{{ issue }}
            </p>
          </div>
        </div>

        <!-- Summary -->
        <div v-if="process.summary" class="flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2">
          <i class="fa-solid fa-circle-info text-amber-500 text-xs mt-0.5" />
          <p class="text-xs text-amber-800">{{ process.summary }}</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
  max-height: 800px;
  overflow: hidden;
}
.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
