<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { DEMO_MODE } from '@/router';
import { useAuthStore } from '@/stores/auth';

interface MenuItem {
  id: string;
  label: string;
  icon: string;
  requiresAuth?: boolean;
}

interface QuickQuestion {
  id: string;
  question: string;
  icon: string;
}

const emit = defineEmits<{
  (e: 'quick-question', question: string): void;
  (e: 'new-chat'): void;
}>();

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const isQuickQuestionsOpen = ref(true);
const isUserMenuOpen = ref(false);

const quickQuestions: QuickQuestion[] = [
  { id: 'courses', question: '人工智能专业的核心课程与实践环节如何安排？', icon: 'fa-book-open' },
  { id: 'path', question: '毕业设计与学习路径有哪些关键要求？', icon: 'fa-route' },
  { id: 'rag', question: 'RAG 在专业知识问答里解决了什么问题？', icon: 'fa-microchip' },
  { id: 'sources', question: '来源片段和重排结果应该如何理解？', icon: 'fa-magnifying-glass-chart' },
];

const allMenuItems: MenuItem[] = [
  { id: 'manual', label: '问答工作台', icon: 'fa-solid fa-comments' },
  { id: 'graph', label: '知识图谱', icon: 'fa-solid fa-diagram-project' },
  { id: 'discover', label: '首页', icon: 'fa-solid fa-house' },
  { id: 'history', label: '会话历史', icon: 'fa-solid fa-clock-rotate-left', requiresAuth: true },
  { id: 'spaces', label: '知识空间', icon: 'fa-solid fa-book-open', requiresAuth: true },
];

const menuItems = computed(() => {
  if (DEMO_MODE && !authStore.isAuthenticated) {
    return allMenuItems.filter((item) => !item.requiresAuth);
  }
  return allMenuItems;
});

const activeItem = computed(() => route.name?.toString() || 'manual');

const userLabel = computed(() => {
  if (!authStore.isAuthenticated) {
    return DEMO_MODE ? '访客体验' : '未登录';
  }

  return authStore.currentUser?.nickname || authStore.currentUser?.username || '校园用户';
});

const userMenuHomeLabel = computed(() => '返回首页');

function handleMenuItemClick(itemId: string) {
  if (itemId === 'discover') {
    router.push('/');
    return;
  }

  router.push(`/${itemId}`);
}

function handleNewChat() {
  emit('new-chat');
  router.push('/manual');
}

function handleQuickQuestion(question: string) {
  emit('quick-question', question);
}

function toggleQuickQuestions() {
  isQuickQuestionsOpen.value = !isQuickQuestionsOpen.value;
}

function handleUserMenuClick() {
  isUserMenuOpen.value = !isUserMenuOpen.value;
}

async function handleLogout() {
  await authStore.logout();
  router.push('/manual');
  isUserMenuOpen.value = false;
}
</script>

<template>
  <aside
    class="sidebar relative z-20 flex h-screen w-16 flex-shrink-0 flex-col border-r border-slate-200 bg-[#F9F9FB] transition-all duration-300 lg:w-[260px]"
    role="navigation"
    aria-label="主导航侧边栏"
  >
    <div class="px-5 pb-4 pt-6">
      <div class="flex items-center space-x-3">
        <div class="flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl border border-[rgba(126,91,67,0.14)] bg-white/90 shadow-sm">
          <img src="/校徽.jpg" alt="安信工校徽" class="h-full w-full object-cover" />
        </div>
        <div class="sidebar-text">
          <div class="text-base font-semibold tracking-wide text-slate-800">安信工 AI 助手</div>
          <div class="text-xs font-medium text-[rgba(112,83,69,0.72)]">
            {{ DEMO_MODE ? '人工智能专业知识工作台 · 公开体验' : '人工智能专业知识工作台 · 校园知识入口' }}
          </div>
        </div>
      </div>
    </div>

    <div class="sidebar-scroll flex-1 space-y-4 overflow-y-auto px-3">
      <button
        class="group flex w-full items-center justify-center rounded-full bg-[linear-gradient(135deg,#944b30_0%,#c68453_100%)] px-4 py-2.5 text-white shadow-sm transition-all duration-200 hover:shadow-lg active:scale-95 lg:justify-between"
        @click="handleNewChat"
        aria-label="新建对话"
        title="新建对话"
      >
        <div class="flex items-center space-x-2">
          <i class="fa-solid fa-plus text-sm" />
          <span class="sidebar-text text-sm font-medium">发起新问答</span>
        </div>
      </button>

      <div class="hidden pt-2 lg:block">
        <button class="group flex w-full items-center space-x-2 px-2 py-1.5 text-left" @click="toggleQuickQuestions">
          <i
            :class="['fa-solid w-3 text-center text-[10px] text-slate-400 transition-transform duration-300', isQuickQuestionsOpen ? 'rotate-0' : '-rotate-90']"
            class="fa-chevron-down"
          />
          <span class="text-xs font-semibold text-slate-500 transition-colors group-hover:text-slate-700">快捷提问</span>
        </button>

        <Transition name="slide-fade">
          <div v-show="isQuickQuestionsOpen" class="mt-1 space-y-0.5 overflow-hidden">
            <button
              v-for="q in quickQuestions"
              :key="q.id"
              class="group magnetic-card flex w-full items-start space-x-2.5 rounded-lg px-2 py-2 text-left text-slate-600 transition-all duration-200 hover:bg-slate-200/50 hover:text-slate-900"
              @click="handleQuickQuestion(q.question)"
            >
              <i :class="['fa-solid mt-1 w-4 flex-shrink-0 text-center text-xs text-slate-400 transition-colors group-hover:text-[#8b472f]', q.icon]" />
              <span class="line-clamp-2 break-words pr-2 text-sm leading-snug">{{ q.question }}</span>
            </button>
          </div>
        </Transition>
      </div>

      <hr class="mx-2 hidden border-slate-200/60 lg:block" />

      <nav aria-label="主菜单" class="space-y-1">
        <button
          v-for="item in menuItems"
          :key="item.id"
          :class="[
            'sidebar-item flex w-full items-center rounded-lg px-3 py-2.5 transition-all duration-200',
            activeItem === item.id ? 'bg-[rgba(174,92,63,0.12)] text-[#8b472f] shadow-sm' : 'text-slate-600 hover:bg-[rgba(174,92,63,0.06)] hover:text-slate-900',
          ]"
          @click="handleMenuItemClick(item.id)"
          :title="item.label"
        >
          <i :class="['fa-fw mr-0 flex-shrink-0 text-center text-sm lg:mr-3', item.icon, activeItem === item.id ? 'font-bold text-[#8b472f]' : 'text-slate-500']" />
          <span :class="['sidebar-text text-sm', activeItem === item.id ? 'font-semibold' : 'font-medium']">{{ item.label }}</span>
        </button>
      </nav>
    </div>

    <div class="relative mt-auto border-t border-slate-200/80 bg-[#F9F9FB] p-3 shadow-[0_-4px_12px_rgba(0,0,0,0.02)]">
      <Transition name="fade-slide">
        <div v-if="isUserMenuOpen" class="absolute bottom-[calc(100%+8px)] left-3 z-50 w-[calc(100%-24px)] overflow-hidden rounded-xl border border-slate-100 bg-white py-1.5 shadow-lg">
          <button class="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-slate-700 transition-colors hover:bg-slate-50" @click="handleMenuItemClick('discover')">
            <i class="fa-solid fa-house w-4 text-center text-slate-400" /> {{ userMenuHomeLabel }}
          </button>
          <div class="mx-2 my-1 h-px bg-slate-100"></div>
          <button v-if="authStore.isAuthenticated" class="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-red-600 transition-colors hover:bg-red-50" @click="handleLogout">
            <i class="fa-solid fa-arrow-right-from-bracket w-4 text-center text-red-400" /> 退出登录
          </button>
        </div>
      </Transition>

      <button class="group magnetic-card flex w-full items-center space-x-3 rounded-xl p-2.5 text-left transition-all duration-200 hover:bg-slate-200/50 active:bg-slate-200" @click="handleUserMenuClick">
        <div class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-800 text-white shadow-sm">
          <span class="text-xs font-bold">{{ userLabel.slice(0, 1) }}</span>
        </div>
        <div class="sidebar-text min-w-0 flex-1">
          <div class="truncate text-sm font-semibold text-slate-800">{{ userLabel }}</div>
        </div>
        <i class="sidebar-text fa-solid fa-ellipsis text-slate-400 transition-colors group-hover:text-slate-600" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar-scroll::-webkit-scrollbar {
  width: 4px;
}

.sidebar-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-scroll::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}

.sidebar-scroll:hover::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
}

.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-5px);
  opacity: 0;
}

@media (max-width: 1024px) {
  .sidebar {
    width: 64px;
  }

  .sidebar-text {
    display: none;
  }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.sidebar-item:hover {
  transform: translate3d(4px, -2px, 0);
}
</style>
