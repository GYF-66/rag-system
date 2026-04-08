import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const DEMO_MODE = import.meta.env.PROD
  ? import.meta.env.VITE_PUBLIC_DEMO_MODE === 'true'
  : import.meta.env.VITE_PUBLIC_DEMO_MODE !== 'false';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition || { top: 0 };
  },
  routes: [
    {
      path: '/',
      name: 'discover',
      alias: ['/discover'],
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/spaces',
      name: 'spaces',
      component: () => import('@/views/SpacesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/finance',
      name: 'finance',
      component: () => import('@/views/FinanceView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/manual',
      name: 'manual',
      component: () => import('@/views/ManualView.vue'),
    },
    {
      path: '/graph',
      name: 'graph',
      component: () => import('@/views/GraphView.vue'),
    },
    {
      path: '/space/:id',
      name: 'space-detail',
      component: () => import('@/views/SpaceDetailView.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
});

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    if (DEMO_MODE) {
      next({ name: 'manual' });
      return;
    }

    next({ name: 'login', query: { redirect: to.fullPath } });
    return;
  }

  if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'manual' });
    return;
  }

  next();
});

export { DEMO_MODE };
export default router;
