<script setup lang="ts">
import { ref, computed } from 'vue';
import type { PerspectiveResult, KnowledgeChunk } from '@/types';
import MarkdownRenderer from './MarkdownRenderer.vue';
import { formatSourceSnippet } from '@/utils/ragFormatting';

interface Props {
  perspectives: PerspectiveResult[];
  sources?: KnowledgeChunk[];
}

const props = withDefaults(defineProps<Props>(), {
  sources: () => [],
});

const activeTab = ref(0);
const showSteps = ref(false);

const activePerspective = computed(() => props.perspectives[activeTab.value]);

const hasSteps = computed(() =>
  activePerspective.value?.steps && activePerspective.value.steps.length > 0,
);

const hasSupplementalSources = computed(() =>
  activePerspective.value?.supplemental_sources && activePerspective.value.supplemental_sources.length > 0,
);

function formatDuration(ms?: number) {
  if (typeof ms !== 'number') return '';
  return `${Math.round(ms)} ms`;
}

function formatScore(value?: number) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'n/a';
  return value.toFixed(2);
}

const displaySources = computed(() =>
  (props.sources ?? []).map((source) => ({
    ...source,
    displayText: formatSourceSnippet(source.text),
  })),
);

const stepIcons: Record<string, string> = {
  query_enhance: '✏️',
  supplemental_retrieval: '🔍',
  context_enrich: '🧩',
  llm_generate: '🤖',
};
</script>

<template>
  <div class="perspective-container">
    <!-- Tab 切换栏 -->
    <div class="flex gap-2 border-b border-[rgba(120,85,63,0.14)] pb-0">
      <button
        v-for="(p, idx) in perspectives"
        :key="p.perspective"
        type="button"
        :class="[
          'relative flex items-center gap-2 rounded-t-xl px-4 py-2.5 text-sm font-semibold transition-all',
          activeTab === idx
            ? 'bg-white text-[#2e211d] shadow-[0_-2px_12px_rgba(75,52,39,0.08)] border border-b-0 border-[rgba(120,85,63,0.14)]'
            : 'text-[rgba(94,73,63,0.68)] hover:text-[#4a352d] hover:bg-[rgba(171,104,70,0.06)]',
        ]"
        @click="activeTab = idx"
      >
        <span class="text-base">{{ p.icon }}</span>
        <span>{{ p.name }}</span>
        <span
          v-if="p.duration_ms"
          class="ml-1 rounded-full bg-[rgba(171,104,70,0.08)] px-2 py-0.5 text-[10px] font-medium text-[rgba(94,73,63,0.6)]"
        >
          {{ formatDuration(p.duration_ms) }}
        </span>
        <span
          v-if="p.error"
          class="ml-1 h-2 w-2 rounded-full bg-red-400"
          title="生成异常"
        />
      </button>
    </div>

    <!-- 活跃视角内容 -->
    <div v-if="activePerspective" class="pt-4">
      <div v-if="activePerspective.tagline" class="mb-3 flex items-center gap-2">
        <span class="text-lg">{{ activePerspective.icon }}</span>
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-[rgba(112,83,69,0.6)]">
          {{ activePerspective.tagline }}
        </span>
      </div>

      <!-- 推理步骤指示器 -->
      <div v-if="hasSteps" class="mb-3">
        <button
          type="button"
          class="flex items-center gap-1.5 text-[11px] font-medium text-[rgba(94,73,63,0.55)] transition hover:text-[rgba(94,73,63,0.85)]"
          @click="showSteps = !showSteps"
        >
          <span class="transition-transform" :class="{ 'rotate-90': showSteps }">▶</span>
          <span>推理步骤（{{ activePerspective.steps!.length }} 步）</span>
        </button>
        <div v-if="showSteps" class="mt-2 flex flex-wrap gap-2">
          <span
            v-for="s in activePerspective.steps"
            :key="s.step"
            class="inline-flex items-center gap-1 rounded-full border border-[rgba(120,85,63,0.12)] bg-[rgba(171,104,70,0.04)] px-2.5 py-1 text-[11px] text-[rgba(94,73,63,0.7)]"
          >
            <span>{{ stepIcons[s.step] || '⚡' }}</span>
            <span>{{ s.description }}</span>
            <span v-if="s.duration_ms" class="font-mono text-[10px] text-[rgba(94,73,63,0.45)]">{{ formatDuration(s.duration_ms) }}</span>
          </span>
        </div>
      </div>

      <div v-if="activePerspective.error" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        视角生成异常：{{ activePerspective.error }}
      </div>

      <MarkdownRenderer v-else :content="activePerspective.response" />

      <!-- 视角补充来源 -->
      <div
        v-if="hasSupplementalSources"
        class="mt-3 space-y-2 rounded-xl border border-[rgba(120,85,63,0.1)] bg-[rgba(171,104,70,0.02)] p-3"
      >
        <p class="text-[11px] font-semibold tracking-[0.14em] text-[rgba(112,83,69,0.5)]">
          {{ activePerspective.icon }} 补充检索（{{ activePerspective.supplemental_sources!.length }} 条）
        </p>
        <div
          v-for="(ss, i) in activePerspective.supplemental_sources"
          :key="`ss-${i}`"
          class="rounded-lg border border-[rgba(120,85,63,0.08)] bg-white px-3 py-2 text-[12px] text-[rgba(75,52,39,0.7)]"
        >
          <span v-if="ss.section" class="mr-2 rounded bg-[rgba(171,104,70,0.08)] px-1.5 py-0.5 text-[10px] font-medium text-[rgba(112,83,69,0.6)]">
            {{ ss.section }}
          </span>
          {{ ss.text }}
        </div>
      </div>
    </div>

    <!-- 共享引用来源 -->
    <div
      v-if="displaySources.length"
      class="mt-4 space-y-3 border-t border-slate-200 pt-3"
      data-testid="perspective-source-block"
    >
      <div class="flex items-center justify-between gap-3">
        <p class="text-xs font-semibold tracking-[0.16em] text-slate-500">共享引用片段</p>
        <span class="text-[11px] text-slate-400">{{ displaySources.length }} 条参考片段</span>
      </div>

      <article
        v-for="(source, index) in displaySources"
        :key="`${source.id}-${index}`"
        class="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600"
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
        <p class="mt-3 whitespace-pre-line leading-7 text-slate-700">{{ source.displayText }}</p>
      </article>
    </div>
  </div>
</template>
