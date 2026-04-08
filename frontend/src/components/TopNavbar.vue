<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { DEMO_MODE } from '@/router';
import { useAuthStore } from '@/stores/auth';

interface NavItem {
  id: string;
  label: string;
  to: string;
}

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const isScrolled = ref(false);

function updateScrollState() {
  isScrolled.value = window.scrollY > 18;
}

onMounted(() => {
  updateScrollState();
  window.addEventListener('scroll', updateScrollState, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updateScrollState);
});

const navItems = computed<NavItem[]>(() => {
  const items: NavItem[] = [
    { id: 'discover', label: '公共首页', to: '/' },
    { id: 'manual', label: '专业学习工作台', to: '/manual' },
    { id: 'graph', label: '知识图谱', to: '/graph' },
  ];

  if (authStore.isAuthenticated) {
    items.push(
      { id: 'history', label: '会话历史', to: '/history' },
      { id: 'spaces', label: '知识空间', to: '/spaces' },
    );
  }

  return items;
});

const brandSubtitle = computed(() => {
  if (authStore.isAuthenticated) {
    return '专业学习主视觉 · 已登录工作台';
  }
  if (DEMO_MODE) {
    return '专业学习主视觉 · 公开体验模式';
  }
  return '专业学习主视觉 · AI 专业知识入口';
});

const userLabel = computed(() => {
  if (!authStore.isAuthenticated) {
    return DEMO_MODE ? '访客体验' : '未登录';
  }

  return authStore.currentUser?.nickname || authStore.currentUser?.username || '校园用户';
});

const primaryActionLabel = computed(() => {
  if (authStore.isAuthenticated) return '继续问答';
  if (DEMO_MODE) return '立即体验';
  return '登录进入';
});

const secondaryActionLabel = computed(() => {
  if (authStore.isAuthenticated) return '知识空间';
  if (DEMO_MODE) return '公共首页';
  return '注册账号';
});

function isActive(item: NavItem) {
  if (item.id === 'discover') {
    return route.name === 'discover';
  }

  return route.path === item.to || route.path.startsWith(`${item.to}/`);
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
    router.push('/');
    return;
  }

  router.push('/register');
}

function handleBrandClick() {
  router.push('/');
}
</script>

<template>
  <nav class="topbar-shell" :class="{ 'topbar-shell--scrolled': isScrolled }">
    <button class="topbar-brand" type="button" @click="handleBrandClick">
      <span class="topbar-brand-mark">
        <img src="/校徽.jpg" alt="安徽信息工程学院校徽" class="topbar-brand-emblem" />
      </span>
      <span class="topbar-brand-copy">
        <strong>AIIT 专业学习工作台</strong>
        <small>{{ brandSubtitle }}</small>
      </span>
    </button>

    <div class="topbar-links">
      <button
        v-for="item in navItems"
        :key="item.id"
        type="button"
        class="topbar-link"
        :class="{ 'topbar-link--active': isActive(item) }"
        @click="router.push(item.to)"
      >
        {{ item.label }}
      </button>
    </div>

    <div class="topbar-actions">
      <div class="topbar-user" :class="{ 'topbar-user--guest': !authStore.isAuthenticated }">
        <span class="topbar-user-dot"></span>
        <span>{{ userLabel }}</span>
      </div>

      <button class="topbar-ghost magnetic-card" type="button" @click="handleSecondaryAction">
        <i class="fa-solid fa-grid-2" />
        <span>{{ secondaryActionLabel }}</span>
      </button>

      <button class="topbar-primary magnetic-card" type="button" @click="handlePrimaryAction">
        <span>{{ primaryActionLabel }}</span>
        <i class="fa-solid fa-arrow-right-long" />
      </button>
    </div>
  </nav>
</template>

<style scoped>
.topbar-shell {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 5rem;
  padding: 1rem 1.4rem;
  background: linear-gradient(180deg, rgba(255, 251, 246, 0.92), rgba(250, 244, 236, 0.8));
  border-bottom: 1px solid rgba(126, 91, 67, 0.14);
  backdrop-filter: blur(var(--motion-nav-blur, 16px)) saturate(145%);
  transition:
    background-color var(--motion-duration-base, 320ms) var(--motion-ease-standard, ease),
    border-color var(--motion-duration-base, 320ms) var(--motion-ease-standard, ease),
    box-shadow var(--motion-duration-base, 320ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-base, 320ms) var(--motion-ease-standard, ease);
}

.topbar-shell--scrolled {
  background: linear-gradient(180deg, rgba(255, 251, 246, 0.97), rgba(247, 239, 231, 0.92));
  border-bottom-color: rgba(126, 91, 67, 0.18);
  box-shadow: 0 20px 50px rgba(67, 44, 34, 0.08);
}

.topbar-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.9rem;
  min-width: 0;
  color: #2f221e;
  text-align: left;
  transition: transform var(--motion-duration-fast, 180ms) ease;
}

.topbar-brand:hover {
  transform: translate3d(0, -1px, 0);
}

.topbar-brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(126, 91, 67, 0.16);
  box-shadow: 0 14px 32px rgba(91, 61, 48, 0.12);
  overflow: hidden;
}

.topbar-brand-emblem {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.topbar-brand-copy {
  display: grid;
  min-width: 0;
}

.topbar-brand-copy strong {
  font-size: 1rem;
  font-weight: 900;
  letter-spacing: 0.03em;
}

.topbar-brand-copy small {
  color: rgba(95, 72, 61, 0.74);
  font-size: 0.74rem;
  letter-spacing: 0.08em;
}

.topbar-links {
  display: none;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem;
  border-radius: 999px;
  border: 1px solid rgba(126, 91, 67, 0.12);
  background: rgba(255, 251, 246, 0.74);
}

.topbar-link,
.topbar-ghost,
.topbar-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  border-radius: 999px;
  transition: transform 180ms ease, background-color 180ms ease, color 180ms ease, box-shadow 180ms ease;
}

.topbar-link {
  padding: 0.72rem 1rem;
  color: rgba(89, 63, 51, 0.8);
  border: 1px solid transparent;
  font-size: 0.92rem;
  font-weight: 600;
}

.topbar-link:hover,
.topbar-link--active {
  color: #8b472f;
  background: rgba(174, 92, 63, 0.09);
  box-shadow: 0 10px 24px rgba(91, 61, 48, 0.08);
  transform: translate3d(0, -1px, 0);
}

.topbar-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
}

.topbar-user {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.7rem 0.9rem;
  border-radius: 999px;
  border: 1px solid rgba(126, 91, 67, 0.12);
  background: rgba(255, 255, 255, 0.64);
  color: #4d382f;
  font-size: 0.82rem;
  font-weight: 700;
  transition: transform var(--motion-duration-fast, 180ms) ease, box-shadow var(--motion-duration-fast, 180ms) ease;
}

.topbar-user:hover {
  transform: translate3d(0, -1px, 0);
  box-shadow: 0 12px 24px rgba(91, 61, 48, 0.08);
}

.topbar-user--guest {
  color: rgba(97, 74, 62, 0.72);
}

.topbar-user-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #8ea459, #d7b560);
  box-shadow: 0 0 0 4px rgba(143, 164, 89, 0.12);
}

.topbar-ghost {
  padding: 0.76rem 1rem;
  color: #5c4439;
  border: 1px solid rgba(126, 91, 67, 0.16);
  background: rgba(255, 255, 255, 0.72);
  font-size: 0.88rem;
  font-weight: 700;
}

.topbar-primary {
  padding: 0.8rem 1.12rem;
  color: #fff7f0;
  border: 1px solid rgba(140, 63, 44, 0.22);
  background: linear-gradient(135deg, #944b30 0%, #c68453 100%);
  box-shadow: 0 14px 28px rgba(140, 63, 44, 0.18);
  font-size: 0.88rem;
  font-weight: 800;
}

.topbar-ghost:hover,
.topbar-primary:hover {
  transform: translateY(-1px);
}

@media (min-width: 1100px) {
  .topbar-links {
    display: inline-flex;
  }
}

@media (max-width: 960px) {
  .topbar-brand-copy small,
  .topbar-links,
  .topbar-ghost span,
  .topbar-user {
    display: none;
  }

  .topbar-shell {
    padding-inline: 1rem;
  }
}
</style>
