<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import LibraryMasthead from '@/components/LibraryMasthead.vue';
import MobileNav from '@/components/MobileNav.vue';
import Sidebar from '@/components/Sidebar.vue';
import TopNavbar from '@/components/TopNavbar.vue';

interface FinanceRecord {
  id: string;
  type: 'income' | 'expense';
  category: string;
  amount: number;
  description: string;
  date: string;
  status: 'completed' | 'pending';
}

const router = useRouter();

const financeRecords = ref<FinanceRecord[]>([
  {
    id: '1',
    type: 'income',
    category: '奖学金',
    amount: 5000,
    description: '2024 秋季学期奖学金到账记录',
    date: '2024-01-15',
    status: 'completed',
  },
  {
    id: '2',
    type: 'expense',
    category: '学费',
    amount: 4500,
    description: '2024 春季学期学费缴纳',
    date: '2024-01-10',
    status: 'completed',
  },
  {
    id: '3',
    type: 'expense',
    category: '住宿费',
    amount: 1200,
    description: '2024 春季学期住宿费用待处理',
    date: '2024-01-10',
    status: 'pending',
  },
]);

const stats = computed(() => {
  const totalIncome = financeRecords.value.filter((record) => record.type === 'income').reduce((sum, record) => sum + record.amount, 0);
  const totalExpense = financeRecords.value.filter((record) => record.type === 'expense').reduce((sum, record) => sum + record.amount, 0);
  return {
    totalIncome,
    totalExpense,
    balance: totalIncome - totalExpense,
  };
});

function handleQuickQuestion(question: string) {
  router.push({ path: '/manual', query: { q: question } });
}

function handleNewChat() {
  router.push('/manual');
}
</script>

<template>
  <div class="flex h-screen workspace-bg">
    <Sidebar @quick-question="handleQuickQuestion" @new-chat="handleNewChat" />

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <TopNavbar />

      <main class="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        <div class="mx-auto flex w-full max-w-7xl flex-col gap-6">
          <LibraryMasthead
            eyebrow="Finance"
            title="财务总览"
            description="在统一的校园 RAG 知识体系下，财务页承担学费、奖助记录与费用状态的展示入口，保持与其他页面一致的语气和视觉。"
            icon="fa-regular fa-credit-card"
            :pills="['财务记录', '奖助信息', '状态查看', '校园语气']"
            :stats="[
              { label: '总收入', value: `¥${stats.totalIncome.toLocaleString()}` },
              { label: '总支出', value: `¥${stats.totalExpense.toLocaleString()}` },
              { label: '当前余额', value: `¥${stats.balance.toLocaleString()}` },
            ]"
          >
            <template #aside>
              <div class="space-y-3 text-sm leading-7 text-[rgba(255,248,241,0.82)]">
                <p class="text-xs uppercase tracking-[0.24em] text-[rgba(255,248,241,0.56)]">Finance View</p>
                <p>该页面保持前端静态展示逻辑，但视觉和叙事已经接入校园知识系统，不再像独立后台模块。</p>
              </div>
            </template>
          </LibraryMasthead>

          <section class="grid gap-4 md:grid-cols-3">
            <article class="workspace-card glow-hover reveal-item rounded-[28px] p-5" v-reveal>
              <p class="text-sm text-[rgba(112,83,69,0.72)]">总收入</p>
              <h2 class="mt-3 text-3xl font-black text-emerald-600">¥{{ stats.totalIncome.toLocaleString() }}</h2>
            </article>
            <article class="workspace-card glow-hover reveal-item rounded-[28px] p-5" v-reveal="80">
              <p class="text-sm text-[rgba(112,83,69,0.72)]">总支出</p>
              <h2 class="mt-3 text-3xl font-black text-red-500">¥{{ stats.totalExpense.toLocaleString() }}</h2>
            </article>
            <article class="workspace-card glow-hover reveal-item rounded-[28px] p-5" v-reveal="160">
              <p class="text-sm text-[rgba(112,83,69,0.72)]">余额</p>
              <h2 class="mt-3 text-3xl font-black" :class="stats.balance >= 0 ? 'text-[#8b472f]' : 'text-red-500'">¥{{ stats.balance.toLocaleString() }}</h2>
            </article>
          </section>

          <section class="workspace-card reveal-item rounded-[30px] overflow-hidden" v-reveal="220">
            <div class="border-b border-[rgba(120,85,63,0.14)] px-6 py-5">
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[rgba(112,83,69,0.72)]">Records</p>
              <h2 class="mt-2 text-2xl font-black text-[#281d19]">财务记录</h2>
            </div>
            <div class="divide-y divide-[rgba(120,85,63,0.12)]">
              <article v-for="record in financeRecords" :key="record.id" class="flex flex-col gap-4 px-6 py-5 md:flex-row md:items-center md:justify-between">
                <div class="flex items-start gap-4">
                  <div class="flex h-12 w-12 items-center justify-center rounded-2xl" :class="record.type === 'income' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'">
                    <i :class="record.type === 'income' ? 'fa-solid fa-arrow-down' : 'fa-solid fa-arrow-up'" />
                  </div>
                  <div>
                    <div class="flex flex-wrap items-center gap-3">
                      <h3 class="text-lg font-semibold text-[#2f221f]">{{ record.category }}</h3>
                      <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="record.status === 'completed' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'">
                        {{ record.status === 'completed' ? '已完成' : '处理中' }}
                      </span>
                    </div>
                    <p class="mt-2 text-sm leading-7 text-[rgba(76,58,49,0.78)]">{{ record.description }}</p>
                    <p class="mt-1 text-xs text-[rgba(112,83,69,0.68)]">{{ record.date }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="text-2xl font-black" :class="record.type === 'income' ? 'text-emerald-600' : 'text-red-500'">
                    {{ record.type === 'income' ? '+' : '-' }}¥{{ record.amount.toLocaleString() }}
                  </p>
                </div>
              </article>
            </div>
          </section>
        </div>
      </main>

      <MobileNav />
    </div>
  </div>
</template>
