const CHINESE_ORDERED_RE = /^(?:[一二三四五六七八九十]+[、.．]|\d+[、.．)])/u;
const LIST_PREFIX_RE = /^(?:[-*•]\s*|\d+[、.．)]\s*|[一二三四五六七八九十]+[、.．]\s*)/u;
const HEADING_RE = /^\*\*[^*\n]{2,40}\*\*[:：]?$/u;
const HEADING_WITH_BODY_RE = /^(\*\*[^*\n]{2,40}\*\*[:：]?)(.+)$/u;
const SENTENCE_RE = /[^。！？；\n]+[。！？；]?/gu;

function normalizeText(content: string): string {
  return content
    .replace(/\r\n?/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[\t ]{2,}/g, ' ')
    .trim();
}

function splitSentences(text: string): string[] {
  const sentences = text.match(SENTENCE_RE) ?? [text];
  return sentences
    .map((sentence) => sentence.trim())
    .filter(Boolean)
    .map((sentence) => (/[。！？；]$/u.test(sentence) ? sentence : `${sentence}。`));
}

function groupSentences(sentences: string[], maxChars = 64, maxSentencesPerGroup = 2): string[] {
  const groups: string[] = [];
  let current = '';
  let count = 0;

  for (const sentence of sentences) {
    if (current && (current.length + sentence.length > maxChars || count >= maxSentencesPerGroup)) {
      groups.push(current.trim());
      current = sentence;
      count = 1;
      continue;
    }

    current += sentence;
    count += 1;
  }

  if (current) {
    groups.push(current.trim());
  }

  return groups;
}

function normalizeInlineEnumeration(text: string): string {
  return text
    .replace(/([：:])\s*(?=(?:\d+[、.．)]|[一二三四五六七八九十]+[、.．]))/gu, '$1\n')
    .replace(/(?<=[。；\n])\s*(?=(?:\d+[、.．)]|[一二三四五六七八九十]+[、.．]))/gu, '\n');
}

function toListBlock(lines: string[]): string {
  return lines
    .map((line) => line.replace(LIST_PREFIX_RE, '').trim())
    .filter(Boolean)
    .map((line) => `- ${line}`)
    .join('\n');
}

function splitLongParagraph(block: string): string[] {
  const trimmed = block.trim();
  if (!trimmed) {
    return [];
  }

  const normalized = trimmed.replace(/\n+/g, ' ');
  const sentences = splitSentences(normalized);
  if (sentences.length <= 1) {
    return [normalized];
  }
  if (sentences.length <= 2 && normalized.length < 90) {
    return [normalized];
  }

  return groupSentences(sentences, 72, 2);
}

function expandPseudoHeadings(lines: string[]): string[] {
  const expanded: string[] = [];
  for (const line of lines) {
    const match = line.match(HEADING_WITH_BODY_RE);
    if (match) {
      expanded.push(match[1].trim());
      expanded.push(match[2].trim());
      continue;
    }
    expanded.push(line);
  }
  return expanded;
}

export function preprocessRagMarkdown(content: string): string {
  const normalized = normalizeInlineEnumeration(normalizeText(content));
  if (!normalized) {
    return '';
  }

  const rawBlocks = normalized.split(/\n\s*\n/).map((block) => block.trim()).filter(Boolean);
  const outputBlocks: string[] = [];

  for (const block of rawBlocks) {
    const lines = expandPseudoHeadings(block.split('\n').map((line) => line.trim()).filter(Boolean));
    if (!lines.length) {
      continue;
    }

    const introLines: string[] = [];
    const listLines: string[] = [];

    for (const line of lines) {
      if (HEADING_RE.test(line)) {
        if (introLines.length) {
          outputBlocks.push(...splitLongParagraph(introLines.join(' ')));
          introLines.length = 0;
        }
        if (listLines.length) {
          outputBlocks.push(toListBlock(listLines));
          listLines.length = 0;
        }
        outputBlocks.push(line);
        continue;
      }

      if (CHINESE_ORDERED_RE.test(line) || /^[-*•]\s+/u.test(line)) {
        listLines.push(line);
        continue;
      }

      if (listLines.length) {
        outputBlocks.push(toListBlock(listLines));
        listLines.length = 0;
      }
      introLines.push(line);
    }

    if (introLines.length) {
      outputBlocks.push(...splitLongParagraph(introLines.join(' ')));
    }
    if (listLines.length) {
      outputBlocks.push(toListBlock(listLines));
    }
  }

  return outputBlocks.join('\n\n').replace(/\n{3,}/g, '\n\n').trim();
}

export function formatSourceSnippet(content: string): string {
  const normalized = normalizeInlineEnumeration(normalizeText(content));
  if (!normalized) {
    return '';
  }

  const sentences = splitSentences(normalized.replace(/\n+/g, ' '));
  if (sentences.length <= 1) {
    return normalized;
  }

  return groupSentences(sentences.slice(0, 4), 60, 2).slice(0, 2).join('\n\n');
}
