<script setup lang="ts">
/**
 * 快速启动项类型
 */
interface QuickAction {
  id: string;
  emoji: string;
  label: string;
  query: string;
}

/**
 * 快速启动数据 - AI 专业课程相关
 */
const quickActions: QuickAction[] = [
  {
    id: 'ml',
    emoji: '🤖',
    label: '机器学习',
    query: '机器学习课程主要学什么？'
  },
  {
    id: 'dl',
    emoji: '🧠',
    label: '深度学习',
    query: '深度学习与神经网络的核心内容？'
  },
  {
    id: 'plan',
    emoji: '📋',
    label: '培养方案',
    query: '人工智能专业培养方案是什么？'
  },
  {
    id: 'cv',
    emoji: '👁️',
    label: '计算机视觉',
    query: '计算机视觉应用开发学什么？'
  },
  {
    id: 'python',
    emoji: '🐍',
    label: 'Python数据分析',
    query: 'Python数据处理与分析课程内容？'
  },
  {
    id: 'core',
    emoji: '📚',
    label: '核心课程',
    query: '人工智能专业有哪些核心课程？'
  }
];

/**
 * 定义组件 emits
 */
interface Emits {
  'select': [query: string];
}

const emit = defineEmits<Emits>();

/**
 * 处理快速启动按钮点击
 */
const handleActionClick = (action: QuickAction) => {
  emit('select', action.query);
};
</script>

<template>
  <div class="mt-6 flex flex-wrap justify-center gap-2">
    <button
      v-for="action in quickActions"
      :key="action.id"
      class="quick-pill flex items-center space-x-1.5 px-3 py-1.5 text-gray-600 text-sm"
      @click="handleActionClick(action)"
    >
      <span>{{ action.emoji }}</span>
      <span>{{ action.label }}</span>
    </button>
  </div>
</template>

<style scoped>
/* Perplexity 风格 pill 按钮 */
.quick-pill {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  transition: all 0.15s ease;
}

.quick-pill:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.quick-pill:active {
  transform: scale(0.98);
}
</style>