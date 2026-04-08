<script setup lang="ts">
import KnowledgeGraph from '@/components/KnowledgeGraph.vue';
import Sidebar from '@/components/Sidebar.vue';
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-slate-50">
    <Sidebar />
    <main class="flex-1 flex flex-col min-w-0 p-4 overflow-hidden">
      <KnowledgeGraph class="flex-1" />
    </main>
  </div>
</template>
