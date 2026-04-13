<template>
  <div
    :class="['markdown-body', { 'markdown-typewriter': typewriter }]"
    data-testid="answer-rich-text"
    v-html="renderedHtml"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { preprocessRagMarkdown } from '@/utils/ragFormatting';

const props = withDefaults(
  defineProps<{
    content: string;
    sanitize?: boolean;
    typewriter?: boolean;
  }>(),
  {
    sanitize: true,
    typewriter: false,
  },
);

marked.setOptions({
  breaks: true,
  gfm: true,
});

const renderedHtml = computed(() => {
  if (!props.content) return '';
  const prepared = preprocessRagMarkdown(props.content);
  const raw = marked.parse(prepared) as string;
  return props.sanitize
    ? DOMPurify.sanitize(raw, {
        ADD_ATTR: ['target', 'rel'],
      })
    : raw;
});
</script>

<style scoped>
.markdown-body {
  font-size: 0.95rem;
  line-height: 1.8;
  color: #1f2937;
  word-break: break-word;
}

.markdown-typewriter {
  font-family: var(--font-mono);
  letter-spacing: 0.01em;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 1.35em;
  margin-bottom: 0.7em;
  font-weight: 700;
  line-height: 1.25;
  color: #0f172a;
}

.markdown-body :deep(h1) {
  font-size: 1.5em;
}

.markdown-body :deep(h2) {
  font-size: 1.3em;
}

.markdown-body :deep(h3) {
  font-size: 1.05em;
  letter-spacing: 0.01em;
}

.markdown-body :deep(p) {
  margin: 0.85em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.35em;
  margin: 0.85em 0;
}

.markdown-body :deep(li) {
  margin: 0.45em 0;
  line-height: 1.75;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #3b82f6;
  padding: 0.65em 1em;
  margin: 1em 0;
  background: #eff6ff;
  border-radius: 0 10px 10px 0;
  color: #1e40af;
}

.markdown-body :deep(a) {
  color: #2563eb;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.88em;
  font-family: 'Fira Code', 'Consolas', monospace;
}

.markdown-body :deep(pre) {
  margin: 1em 0;
  padding: 14px;
  overflow-x: auto;
  background: #f8fafc;
  font-size: 0.85rem;
  line-height: 1.6;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  margin: 0.8em 0;
  overflow: hidden;
}

.markdown-body :deep(th) {
  background: #f1f5f9;
  font-weight: 600;
  text-align: left;
  padding: 10px 14px;
  border-bottom: 2px solid #e2e8f0;
}

.markdown-body :deep(td) {
  padding: 8px 14px;
  border-bottom: 1px solid #f1f5f9;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 1.2em 0;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 8px;
}

.markdown-body :deep(strong) {
  font-weight: 700;
  color: #0f172a;
}
</style>
