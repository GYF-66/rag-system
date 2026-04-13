<script setup lang="ts">
import { computed, ref } from 'vue';
import KnowledgeGraph from '@/components/KnowledgeGraph.vue';
import LibraryMasthead from '@/components/LibraryMasthead.vue';
import Sidebar from '@/components/Sidebar.vue';
import TopNavbar from '@/components/TopNavbar.vue';

type WorkspaceState = {
  nodeCount: number;
  edgeCount: number;
  communityCount: number;
  filterLabel: string;
  activeTab: 'graph' | 'alignment';
  activeTabLabel: string;
};

const workspaceState = ref<WorkspaceState>({
  nodeCount: 0,
  edgeCount: 0,
  communityCount: 0,
  filterLabel: '全部节点',
  activeTab: 'graph',
  activeTabLabel: '知识地图',
});

const stats = computed(() => [
  { label: '节点', value: `${workspaceState.value.nodeCount}` },
  { label: '关系', value: `${workspaceState.value.edgeCount}` },
  { label: '社区', value: `${workspaceState.value.communityCount}` },
  { label: '当前筛选', value: workspaceState.value.filterLabel },
]);

const pills = ['Curriculum Atlas', 'GraphRAG Navigation', 'Program Diagnostics'];

function handleWorkspaceState(state: WorkspaceState) {
  workspaceState.value = state;
}
</script>

<template>
  <div class="graph-page workspace-bg" data-testid="graph-page">
    <Sidebar />

    <div class="graph-page__body">
      <TopNavbar />

      <main class="graph-page__main">
        <LibraryMasthead
          eyebrow="Academic Knowledge Map"
          title="知识图谱工作台"
          description="借鉴大学图书馆、课程地图与研究院门户的叙事方式，把课程、知识点与培养目标组织成可探索、可诊断、可回到节点档案的学术空间。"
          icon="fa-solid fa-diagram-project"
          :pills="pills"
          :stats="stats"
          intensity="high"
          class="graph-page__masthead"
        >
          <template #aside>
            <div class="graph-page__brief">
              <p class="graph-page__brief-label">Curatorial Note</p>
              <h2>{{ workspaceState.activeTabLabel }}</h2>
              <dl class="graph-page__brief-grid">
                <div>
                  <dt>当前筛选</dt>
                  <dd>{{ workspaceState.filterLabel }}</dd>
                </div>
                <div>
                  <dt>观察重点</dt>
                  <dd>课程结构与能力覆盖</dd>
                </div>
                <div>
                  <dt>界面气质</dt>
                  <dd>馆藏感、学院感、研究感</dd>
                </div>
              </dl>
            </div>
          </template>
        </LibraryMasthead>

        <KnowledgeGraph class="graph-page__workspace" @state-change="handleWorkspaceState" />
      </main>
    </div>
  </div>
</template>

<style scoped>
.graph-page {
  display: flex;
  min-height: 100vh;
}

.graph-page__body {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
}

.graph-page__main {
  flex: 1;
  overflow-y: auto;
  padding: 1.2rem 1rem 2.4rem;
}

.graph-page__masthead {
  margin: 0 auto 1.1rem;
  width: min(100%, 1360px);
}

.graph-page__masthead :deep(.library-scene__art) {
  background:
    linear-gradient(90deg, rgba(34, 22, 18, 0.7), rgba(34, 22, 18, 0.24) 46%, rgba(34, 22, 18, 0.52)),
    linear-gradient(180deg, rgba(14, 11, 10, 0.18), rgba(14, 11, 10, 0.08) 36%, rgba(14, 11, 10, 0.42)),
    url('/aiit-campus-hero.jpg') center 52% / cover no-repeat;
}

.graph-page__masthead :deep(.library-scene__svg),
.graph-page__masthead :deep(.library-scene__cloud),
.graph-page__masthead :deep(.library-scene__clouds),
.graph-page__masthead :deep(.library-scene__mist),
.graph-page__masthead :deep(.library-scene__bloom),
.graph-page__masthead :deep(.library-scene__wash),
.graph-page__masthead :deep(.library-scene__grain),
.graph-page__masthead :deep(.library-scene__light) {
  opacity: 0.18;
}

.graph-page__masthead :deep(.library-masthead__eyebrow),
.graph-page__masthead :deep(.library-masthead__description),
.graph-page__masthead :deep(.library-masthead__pill),
.graph-page__masthead :deep(.library-masthead__stat span) {
  color: rgba(255, 247, 240, 0.88);
}

.graph-page__masthead :deep(.library-masthead__headline h1),
.graph-page__masthead :deep(.library-masthead__stat strong) {
  color: #fffaf5;
}

.graph-page__masthead :deep(.library-masthead__pill),
.graph-page__masthead :deep(.library-masthead__stat) {
  border-color: rgba(255, 246, 238, 0.14);
  background: rgba(44, 29, 24, 0.24);
  backdrop-filter: blur(10px);
}

.graph-page__masthead :deep(.library-masthead__icon) {
  background: linear-gradient(135deg, rgba(160, 75, 48, 0.98), rgba(213, 155, 78, 0.92));
}

.graph-page__brief {
  display: grid;
  gap: 0.9rem;
}

.graph-page__brief-label {
  margin: 0;
  color: rgba(255, 243, 231, 0.72);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.graph-page__brief h2 {
  margin: 0;
  color: #fff9f2;
  font-family: var(--font-display);
  font-size: 1.55rem;
}

.graph-page__brief-grid {
  display: grid;
  gap: 0.75rem;
}

.graph-page__brief-grid div {
  display: grid;
  gap: 0.22rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid rgba(255, 246, 238, 0.1);
  border-radius: 1rem;
  background: rgba(255, 249, 241, 0.06);
}

.graph-page__brief-grid dt {
  color: rgba(255, 243, 231, 0.62);
  font-size: 0.72rem;
}

.graph-page__brief-grid dd {
  margin: 0;
  color: #fffaf5;
  font-size: 0.94rem;
  font-weight: 700;
}

.graph-page__workspace {
  margin: 0 auto;
  width: min(100%, 1360px);
}

@media (max-width: 768px) {
  .graph-page__main {
    padding-inline: 0.75rem;
  }

  .graph-page__brief h2 {
    font-size: 1.35rem;
  }
}
</style>
