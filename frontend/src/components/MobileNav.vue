<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { DEMO_MODE } from '@/router';
import { useAuthStore } from '@/stores/auth';

interface NavItem {
  id: string;
  label: string;
  icon: string;
  to: string;
  requiresAuth?: boolean;
}

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const allNavItems: NavItem[] = [
  { id: 'discover', label: '首页', icon: 'fa-solid fa-house', to: '/' },
  { id: 'manual', label: '问答', icon: 'fa-solid fa-comments', to: '/manual' },
  { id: 'history', label: '历史', icon: 'fa-solid fa-clock-rotate-left', to: '/history', requiresAuth: true },
  { id: 'spaces', label: '知识库', icon: 'fa-solid fa-book-open', to: '/spaces', requiresAuth: true },
];

const navItems = computed(() => {
  if (DEMO_MODE && !authStore.isAuthenticated) {
    return allNavItems.filter((item) => !item.requiresAuth);
  }

  return allNavItems;
});

function isActive(item: NavItem) {
  if (item.id === 'discover') {
    return route.name === 'discover';
  }

  return route.path === item.to || route.path.startsWith(`${item.to}/`);
}

function handleNavigate(item: NavItem) {
  router.push(item.to);
}
</script>

<template>
  <nav class="mobile-nav lg:hidden" aria-label="移动端导航">
    <div class="mobile-nav__grid" :style="{ gridTemplateColumns: `repeat(${navItems.length}, minmax(0, 1fr))` }">
      <button
        v-for="item in navItems"
        :key="item.id"
        type="button"
        class="mobile-nav__item magnetic-card"
        :class="{ 'mobile-nav__item--active': isActive(item) }"
        @click="handleNavigate(item)"
      >
        <i :class="[item.icon, 'text-base']" />
        <span>{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.mobile-nav {
  position: sticky;
  bottom: 0;
  z-index: 35;
  border-top: 1px solid rgba(126, 91, 67, 0.14);
  background: linear-gradient(180deg, rgba(255, 251, 246, 0.92), rgba(248, 241, 232, 0.86));
  backdrop-filter: blur(18px) saturate(145%);
  box-shadow: 0 -18px 40px rgba(54, 35, 27, 0.08);
}

.mobile-nav__grid {
  display: grid;
  gap: 0.45rem;
  padding: 0.7rem;
}

.mobile-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.32rem;
  min-height: 4rem;
  padding: 0.55rem 0.35rem;
  border-radius: 1.15rem;
  color: rgba(94, 69, 57, 0.72);
  font-size: 0.74rem;
  font-weight: 700;
  transition: background-color 180ms ease, color 180ms ease, transform 180ms ease;
}

.mobile-nav__item:hover {
  color: rgba(90, 60, 49, 0.92);
  background: rgba(174, 92, 63, 0.06);
}

.mobile-nav__item--active {
  color: #8b472f;
  background: rgba(174, 92, 63, 0.12);
  box-shadow: 0 12px 24px rgba(91, 61, 48, 0.08);
}
</style>
