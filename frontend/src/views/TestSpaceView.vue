<script setup lang="ts">
import { ref } from 'vue';

const showModal = ref(false);
const count = ref(0);

function openModal() {
  showModal.value = true;
  count.value += 1;
}

function closeModal() {
  showModal.value = false;
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 p-8">
    <h1 class="text-2xl font-bold mb-6">测试页面</h1>

    <div class="space-y-4">
      <button
        class="px-6 py-3 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600"
        @click="openModal"
      >
        打开 Modal (已点击 {{ count }} 次)
      </button>

      <p class="text-slate-600">Modal 状态: {{ showModal ? '显示' : '隐藏' }}</p>
    </div>

    <transition
      enter-active-class="transition-opacity duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        @click="closeModal"
      >
        <div class="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8" @click.stop>
          <h2 class="text-2xl font-bold mb-4">测试 Modal</h2>
          <p class="text-slate-600 mb-6">如果你能看到这个对话框，说明 Modal 组件工作正常。</p>
          <button
            class="w-full py-3 bg-slate-200 text-slate-700 rounded-xl hover:bg-slate-300"
            @click="closeModal"
          >
            关闭
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>
