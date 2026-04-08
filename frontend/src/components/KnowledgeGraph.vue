<script setup lang="ts">
/**
 * KnowledgeGraph.vue — Three.js 3D 知识图谱可视化
 *
 * 3D 力导向图：节点球体 + 边线 + OrbitControls 旋转/缩放 + 节点拖拽
 */
import { ref, onMounted, onUnmounted, watch, computed, nextTick, shallowRef } from 'vue';
import { apiClient } from '@/services/api';
import type {
  GraphVisualizationData,
  GraphNode,
  GraphSearchResult,
  AlignmentAnalysis,
} from '@/types';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ── 颜色方案 ─────────────────────────────────────────────────────

const NODE_COLORS: Record<string, number> = {
  course: 0x3b82f6,
  concept: 0x10b981,
  requirement: 0xf59e0b,
  indicator: 0x8b5cf6,
  skill: 0xec4899,
  experiment: 0x06b6d4,
};

const NODE_LABELS: Record<string, string> = {
  course: '课程', concept: '知识点', requirement: '毕业要求',
  indicator: '指标点', skill: '能力', experiment: '实验',
};

const NODE_LABELS_CSS: Record<string, string> = {
  course: '#3b82f6', concept: '#10b981', requirement: '#f59e0b',
  indicator: '#8b5cf6', skill: '#ec4899', experiment: '#06b6d4',
};

const EDGE_COLORS: Record<string, number> = {
  prerequisite: 0xef4444,
  leads_to: 0x3b82f6,
  contains: 0xd1d5db,
  supports: 0xf59e0b,
  related: 0xe5e7eb,
  co_required: 0x8b5cf6,
};

// ── 响应式状态 ───────────────────────────────────────────────────

const canvasRef = ref<HTMLDivElement | null>(null);
const loading = ref(true);
const error = ref('');
const graphData = ref<GraphVisualizationData | null>(null);
const searchQuery = ref('');
const searchResult = ref<GraphSearchResult | null>(null);
const alignmentData = ref<AlignmentAnalysis | null>(null);
const activeTab = ref<'graph' | 'alignment'>('graph');
const selectedNodeType = ref<string>('');
const hoveredNode = ref<GraphNode | null>(null);
const tooltipPos = ref({ x: 0, y: 0 });

// ── Three.js 引用 ───────────────────────────────────────────────

interface SimNode extends GraphNode {
  position: THREE.Vector3;
  velocity: THREE.Vector3;
  mesh: THREE.Mesh;
  radius: number;
  pinned: boolean;
  _highlighted?: boolean;
  _isSeed?: boolean;
}

interface SimEdge {
  source: SimNode;
  target: SimNode;
  type: string;
  weight: number;
  line: THREE.Line;
}

const scene = shallowRef<THREE.Scene | null>(null);
const camera = shallowRef<THREE.PerspectiveCamera | null>(null);
const renderer = shallowRef<THREE.WebGLRenderer | null>(null);
const controls = shallowRef<OrbitControls | null>(null);

let simNodes: SimNode[] = [];
let simEdges: SimEdge[] = [];
let animFrameId = 0;
let simulationRunning = false;
let iterationCount = 0;
const MAX_ITERATIONS = 300;

// drag state
let isDragging = false;
let dragNode: SimNode | null = null;
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const dragPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
const intersection = new THREE.Vector3();

// ── 统计 ─────────────────────────────────────────────────────────

const stats = computed(() => graphData.value?.stats ?? null);
const nodeTypeOptions = computed(() => {
  if (!stats.value?.node_types) return [];
  return Object.entries(stats.value.node_types).map(([type, count]) => ({
    type,
    count,
    label: NODE_LABELS[type] || type,
    color: NODE_LABELS_CSS[type] || '#94a3b8',
  }));
});

// ── 数据加载 ─────────────────────────────────────────────────────

async function loadGraphData() {
  loading.value = true;
  error.value = '';
  try {
    graphData.value = await apiClient.getGraphVisualization(selectedNodeType.value || undefined);
    buildGraph();
  } catch (_e: unknown) {
    error.value = (_e instanceof Error ? _e.message : '') || '加载图谱数据失败';
  } finally {
    loading.value = false;
  }
}

async function searchGraph() {
  if (!searchQuery.value.trim()) return;
  try {
    searchResult.value = await apiClient.searchGraph(searchQuery.value, 2, 30);
    if (searchResult.value) {
      const seedIds = new Set(searchResult.value.nodes.filter(n => n.is_seed).map(n => n.id));
      const resultIds = new Set(searchResult.value.nodes.map(n => n.id));
      for (const n of simNodes) {
        n._highlighted = resultIds.has(n.id);
        n._isSeed = seedIds.has(n.id);
        updateNodeAppearance(n);
      }
    }
  } catch (_e: unknown) {
    error.value = (_e instanceof Error ? _e.message : '') || '搜索失败';
  }
}

async function loadAlignment() {
  try {
    alignmentData.value = await apiClient.getAlignmentAnalysis();
  } catch (_e: unknown) {
    error.value = (_e instanceof Error ? _e.message : '') || '加载一致性分析失败';
  }
}

function clearHighlight() {
  searchResult.value = null;
  for (const n of simNodes) {
    n._highlighted = false;
    n._isSeed = false;
    updateNodeAppearance(n);
  }
}

function updateNodeAppearance(n: SimNode) {
  const mat = n.mesh.material as THREE.MeshStandardMaterial;
  const baseColor = NODE_COLORS[n.type] ?? 0x94a3b8;
  if (n._isSeed) {
    mat.color.set(0xef4444);
    mat.emissive.set(0xef4444);
    mat.emissiveIntensity = 0.6;
    n.mesh.scale.setScalar(1.6);
  } else if (n._highlighted) {
    mat.color.set(baseColor);
    mat.emissive.set(baseColor);
    mat.emissiveIntensity = 0.4;
    n.mesh.scale.setScalar(1.3);
  } else {
    mat.color.set(baseColor);
    mat.emissive.set(0x000000);
    mat.emissiveIntensity = 0;
    n.mesh.scale.setScalar(1);
  }
}

// ── Three.js 场景构建 ────────────────────────────────────────────

function initThree() {
  if (!canvasRef.value) return;

  const width = canvasRef.value.clientWidth || 800;
  const height = canvasRef.value.clientHeight || 600;

  // Scene
  const s = new THREE.Scene();
  s.background = new THREE.Color(0xf8fafc);
  s.fog = new THREE.FogExp2(0xf8fafc, 0.0008);
  scene.value = s;

  // Camera
  const cam = new THREE.PerspectiveCamera(60, width / height, 1, 8000);
  cam.position.set(0, 0, 400);
  camera.value = cam;

  // Renderer
  const r = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  r.setSize(width, height);
  r.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  canvasRef.value.appendChild(r.domElement);
  renderer.value = r;

  // Controls
  const ctrl = new OrbitControls(cam, r.domElement);
  ctrl.enableDamping = true;
  ctrl.dampingFactor = 0.08;
  ctrl.minDistance = 50;
  ctrl.maxDistance = 2000;
  ctrl.enablePan = true;
  controls.value = ctrl;

  // Lights
  const ambient = new THREE.AmbientLight(0xffffff, 0.7);
  s.add(ambient);
  const directional = new THREE.DirectionalLight(0xffffff, 0.8);
  directional.position.set(200, 300, 400);
  s.add(directional);
  const point = new THREE.PointLight(0x3b82f6, 0.3, 1500);
  point.position.set(-200, 200, -200);
  s.add(point);

  // Events
  r.domElement.addEventListener('pointerdown', onPointerDown);
  r.domElement.addEventListener('pointermove', onPointerMove);
  r.domElement.addEventListener('pointerup', onPointerUp);
  window.addEventListener('resize', onResize);
}

function buildGraph() {
  if (!graphData.value || !scene.value) return;

  // Clear old
  clearScene();

  const { nodes, edges } = graphData.value;
  const spread = Math.max(200, Math.sqrt(nodes.length) * 15);

  // Nodes
  const sphereGeo = new THREE.SphereGeometry(1, 16, 12);
  simNodes = nodes.map((n) => {
    const radius = n.type === 'course' ? 5 : n.type === 'requirement' ? 4 : 2.5;
    const color = NODE_COLORS[n.type] ?? 0x94a3b8;
    const mat = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.4,
      metalness: 0.1,
    });
    const mesh = new THREE.Mesh(sphereGeo, mat);
    const pos = new THREE.Vector3(
      (Math.random() - 0.5) * spread,
      (Math.random() - 0.5) * spread,
      (Math.random() - 0.5) * spread * 0.5,
    );
    mesh.position.copy(pos);
    mesh.scale.setScalar(radius);
    mesh.userData = { nodeId: n.id };
    scene.value?.add(mesh);

    return {
      ...n,
      position: pos,
      velocity: new THREE.Vector3(),
      mesh,
      radius,
      pinned: false,
    } as SimNode;
  });

  // Node map
  const nodeMap = new Map<string, SimNode>();
  for (const n of simNodes) nodeMap.set(n.id, n);

  // Edges
  simEdges = [];
  for (const e of edges) {
    const source = nodeMap.get(e.source);
    const target = nodeMap.get(e.target);
    if (!source || !target) continue;
    const color = EDGE_COLORS[e.type] ?? 0xe5e7eb;
    const geom = new THREE.BufferGeometry().setFromPoints([source.position, target.position]);
    const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.35 });
    const line = new THREE.Line(geom, mat);
    scene.value?.add(line);
    simEdges.push({ source, target, type: e.type, weight: e.weight || 1, line });
  }

  // Start simulation
  iterationCount = 0;
  simulationRunning = true;
  animate();
}

function clearScene() {
  if (!scene.value) return;
  for (const n of simNodes) {
    scene.value.remove(n.mesh);
    (n.mesh.material as THREE.Material).dispose();
  }
  for (const e of simEdges) {
    scene.value.remove(e.line);
    e.line.geometry.dispose();
    (e.line.material as THREE.Material).dispose();
  }
  simNodes = [];
  simEdges = [];
}

// ── 力导向模拟 (3D) ──────────────────────────────────────────────

function simulateStep() {
  if (iterationCount >= MAX_ITERATIONS) {
    simulationRunning = false;
    return;
  }

  const alpha = 0.3 * Math.pow(0.97, iterationCount);
  const repulsion = 1200;
  const springLen = 60;
  const springK = 0.02;
  const centerK = 0.0005;
  const damping = 0.88;

  // Repulsion (Barnes-Hut simplified: direct N^2 for < 800 nodes)
  for (let i = 0; i < simNodes.length; i++) {
    const a = simNodes[i];
    if (a.pinned) continue;
    for (let j = i + 1; j < simNodes.length; j++) {
      const b = simNodes[j];
      const dx = b.position.x - a.position.x;
      const dy = b.position.y - a.position.y;
      const dz = b.position.z - a.position.z;
      const distSq = dx * dx + dy * dy + dz * dz + 1;
      const dist = Math.sqrt(distSq);
      const force = (repulsion / distSq) * alpha;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      const fz = (dz / dist) * force;
      a.velocity.x -= fx;
      a.velocity.y -= fy;
      a.velocity.z -= fz;
      if (!b.pinned) {
        b.velocity.x += fx;
        b.velocity.y += fy;
        b.velocity.z += fz;
      }
    }
  }

  // Spring (edges)
  for (const edge of simEdges) {
    const { source: a, target: b } = edge;
    const dx = b.position.x - a.position.x;
    const dy = b.position.y - a.position.y;
    const dz = b.position.z - a.position.z;
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
    const force = (dist - springLen) * springK * alpha;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    const fz = (dz / dist) * force;
    if (!a.pinned) { a.velocity.x += fx; a.velocity.y += fy; a.velocity.z += fz; }
    if (!b.pinned) { b.velocity.x -= fx; b.velocity.y -= fy; b.velocity.z -= fz; }
  }

  // Center
  for (const n of simNodes) {
    if (n.pinned) continue;
    n.velocity.x -= n.position.x * centerK * alpha;
    n.velocity.y -= n.position.y * centerK * alpha;
    n.velocity.z -= n.position.z * centerK * alpha;
  }

  // Integrate
  for (const n of simNodes) {
    if (n.pinned) continue;
    n.velocity.multiplyScalar(damping);
    n.position.add(n.velocity);
    n.mesh.position.copy(n.position);
  }

  // Update edges
  for (const e of simEdges) {
    const posArr = e.line.geometry.attributes.position as THREE.BufferAttribute;
    posArr.setXYZ(0, e.source.position.x, e.source.position.y, e.source.position.z);
    posArr.setXYZ(1, e.target.position.x, e.target.position.y, e.target.position.z);
    posArr.needsUpdate = true;
  }

  iterationCount++;
}

// ── 动画循环 ─────────────────────────────────────────────────────

function animate() {
  animFrameId = requestAnimationFrame(animate);

  if (simulationRunning) {
    simulateStep();
  }

  controls.value?.update();
  if (renderer.value && scene.value && camera.value) {
    renderer.value.render(scene.value, camera.value);
  }
}

// ── 交互事件 ─────────────────────────────────────────────────────

function updateMouse(e: PointerEvent) {
  if (!canvasRef.value) return;
  const rect = canvasRef.value.getBoundingClientRect();
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
}

function findNodeUnderPointer(): SimNode | null {
  if (!camera.value) return null;
  raycaster.setFromCamera(mouse, camera.value);
  const meshes = simNodes.map(n => n.mesh);
  const hits = raycaster.intersectObjects(meshes);
  if (hits.length > 0) {
    const nodeId = hits[0].object.userData.nodeId as string;
    return simNodes.find(n => n.id === nodeId) ?? null;
  }
  return null;
}

function onPointerDown(e: PointerEvent) {
  updateMouse(e);
  const node = findNodeUnderPointer();
  if (node) {
    isDragging = true;
    dragNode = node;
    node.pinned = true;
    if (controls.value) controls.value.enabled = false;
    // set drag plane perpendicular to camera
    if (camera.value) {
      const camDir = new THREE.Vector3();
      camera.value.getWorldDirection(camDir);
      dragPlane.setFromNormalAndCoplanarPoint(camDir, node.position);
    }
  }
}

function onPointerMove(e: PointerEvent) {
  updateMouse(e);

  if (isDragging && dragNode && camera.value) {
    raycaster.setFromCamera(mouse, camera.value);
    raycaster.ray.intersectPlane(dragPlane, intersection);
    dragNode.position.copy(intersection);
    dragNode.mesh.position.copy(intersection);
    // update connected edges
    for (const edge of simEdges) {
      if (edge.source === dragNode || edge.target === dragNode) {
        const posArr = edge.line.geometry.attributes.position as THREE.BufferAttribute;
        posArr.setXYZ(0, edge.source.position.x, edge.source.position.y, edge.source.position.z);
        posArr.setXYZ(1, edge.target.position.x, edge.target.position.y, edge.target.position.z);
        posArr.needsUpdate = true;
      }
    }
  } else {
    // Hover
    const node = findNodeUnderPointer();
    hoveredNode.value = node ? simNodes.find(n => n.id === node.id) ?? null : null;
    if (hoveredNode.value && canvasRef.value) {
      const rect = canvasRef.value.getBoundingClientRect();
      tooltipPos.value = { x: e.clientX - rect.left + 14, y: e.clientY - rect.top - 10 };
    }
  }
}

function onPointerUp() {
  if (dragNode) {
    dragNode.pinned = false;
    dragNode = null;
  }
  isDragging = false;
  if (controls.value) controls.value.enabled = true;
}

function onResize() {
  if (!canvasRef.value || !camera.value || !renderer.value) return;
  const w = canvasRef.value.clientWidth;
  const h = canvasRef.value.clientHeight;
  camera.value.aspect = w / h;
  camera.value.updateProjectionMatrix();
  renderer.value.setSize(w, h);
}

// ── 生命周期 ─────────────────────────────────────────────────────

onMounted(async () => {
  await nextTick();
  initThree();
  await loadGraphData();
});

onUnmounted(() => {
  cancelAnimationFrame(animFrameId);
  window.removeEventListener('resize', onResize);
  renderer.value?.domElement.removeEventListener('pointerdown', onPointerDown);
  renderer.value?.domElement.removeEventListener('pointermove', onPointerMove);
  renderer.value?.domElement.removeEventListener('pointerup', onPointerUp);
  clearScene();
  renderer.value?.dispose();
  controls.value?.dispose();
});

watch(selectedNodeType, () => { loadGraphData(); });
watch(activeTab, (tab) => {
  if (tab === 'alignment' && !alignmentData.value) loadAlignment();
});
</script>

<template>
  <div class="flex flex-col h-full bg-white rounded-2xl border border-slate-200 overflow-hidden">
    <!-- 顶部工具栏 -->
    <div class="flex items-center justify-between gap-3 px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
      <div class="flex items-center gap-2">
        <div class="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100">
          <i class="fa-solid fa-diagram-project text-blue-600 text-sm" />
        </div>
        <h3 class="text-sm font-semibold text-slate-700">3D 知识图谱</h3>
        <span v-if="stats" class="text-xs text-slate-400">
          {{ stats.node_count }} 节点 · {{ stats.edge_count }} 边 · {{ stats.community_count }} 社区
        </span>
      </div>

      <div class="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
        <button
          v-for="tab in ([
            { key: 'graph' as const, label: '图谱', icon: 'fa-diagram-project' },
            { key: 'alignment' as const, label: '一致性', icon: 'fa-scale-balanced' },
          ])"
          :key="tab.key"
          class="px-3 py-1.5 text-xs font-medium rounded-md transition-all"
          :class="activeTab === tab.key ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
          @click="activeTab = tab.key"
        >
          <i :class="['fa-solid', tab.icon, 'mr-1']" />
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 图谱面板 -->
    <div v-if="activeTab === 'graph'" class="flex flex-col flex-1 min-h-0">
      <!-- 搜索和筛选栏 -->
      <div class="flex items-center gap-2 px-4 py-2 border-b border-slate-50">
        <div class="relative flex-1 max-w-xs">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索课程、知识点..."
            class="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:border-blue-400 focus:ring-1 focus:ring-blue-200 outline-none transition"
            @keydown.enter="searchGraph"
          />
          <i class="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs" />
        </div>
        <button
          v-if="searchResult"
          class="px-2 py-1.5 text-xs text-slate-500 hover:text-red-500 transition"
          @click="clearHighlight"
        >
          <i class="fa-solid fa-xmark mr-0.5" /> 清除
        </button>

        <div class="flex items-center gap-1 ml-auto">
          <button
            class="px-2 py-1 text-xs rounded-md transition"
            :class="!selectedNodeType ? 'bg-slate-800 text-white' : 'text-slate-500 hover:bg-slate-100'"
            @click="selectedNodeType = ''"
          >
            全部
          </button>
          <button
            v-for="opt in nodeTypeOptions"
            :key="opt.type"
            class="flex items-center gap-1 px-2 py-1 text-xs rounded-md transition"
            :class="selectedNodeType === opt.type ? 'bg-slate-800 text-white' : 'text-slate-500 hover:bg-slate-100'"
            @click="selectedNodeType = opt.type"
          >
            <span class="w-2 h-2 rounded-full inline-block" :style="{ backgroundColor: opt.color }" />
            {{ opt.label }}
            <span class="text-[10px] opacity-60">{{ opt.count }}</span>
          </button>
        </div>
      </div>

      <!-- 搜索结果摘要 -->
      <div v-if="searchResult?.summary" class="px-4 py-2 bg-blue-50 border-b border-blue-100">
        <p class="text-xs text-blue-700 whitespace-pre-line">{{ searchResult.summary }}</p>
      </div>

      <!-- Three.js Canvas -->
      <div class="relative flex-1 min-h-0">
        <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
          <div class="flex flex-col items-center gap-2">
            <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span class="text-xs text-slate-500">加载 3D 知识图谱...</span>
          </div>
        </div>

        <div v-if="error" class="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
          <div class="text-center">
            <i class="fa-solid fa-triangle-exclamation text-amber-500 text-2xl mb-2" />
            <p class="text-sm text-slate-600">{{ error }}</p>
            <button class="mt-2 px-3 py-1 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600" @click="loadGraphData">重试</button>
          </div>
        </div>

        <div ref="canvasRef" class="w-full h-full" />

        <!-- 悬停提示 -->
        <div
          v-if="hoveredNode"
          class="absolute pointer-events-none z-20 px-3 py-2 bg-slate-800 text-white text-xs rounded-lg shadow-lg max-w-xs"
          :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
        >
          <div class="flex items-center gap-1.5 mb-1">
            <span
              class="w-2.5 h-2.5 rounded-full inline-block"
              :style="{ backgroundColor: NODE_LABELS_CSS[hoveredNode.type] || '#94a3b8' }"
            />
            <span class="font-medium">{{ hoveredNode.label }}</span>
          </div>
          <div class="text-[11px] text-slate-300 space-y-0.5">
            <p>类型：{{ NODE_LABELS[hoveredNode.type] || hoveredNode.type }}</p>
            <p v-if="hoveredNode.code">编码：{{ hoveredNode.code }}</p>
            <p v-if="hoveredNode.semester">学期：第{{ hoveredNode.semester }}学期</p>
            <p v-if="hoveredNode.credits">学分：{{ hoveredNode.credits }}</p>
            <p v-if="hoveredNode.community !== undefined">社区：#{{ hoveredNode.community }}</p>
          </div>
        </div>

        <!-- 操作提示 -->
        <div class="absolute bottom-3 right-3 text-[10px] text-slate-400 bg-white/80 backdrop-blur-sm rounded-lg px-3 py-1.5 shadow-sm border border-slate-100">
          <span class="mr-2">鼠标左键拖拽节点</span>
          <span class="mr-2">右键/滚轮旋转缩放</span>
          <span>中键平移</span>
        </div>

        <!-- 图例 -->
        <div class="absolute bottom-3 left-3 flex flex-wrap gap-2 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-sm border border-slate-100">
          <div v-for="(color, type) in NODE_LABELS_CSS" :key="type" class="flex items-center gap-1">
            <span class="w-2.5 h-2.5 rounded-full inline-block" :style="{ backgroundColor: color }" />
            <span class="text-[10px] text-slate-500">{{ NODE_LABELS[type] || type }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 一致性分析面板 -->
    <div v-else-if="activeTab === 'alignment'" class="flex-1 overflow-auto p-4 space-y-4">
      <div v-if="!alignmentData" class="flex items-center justify-center h-40">
        <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
      <template v-else>
        <div class="grid grid-cols-3 gap-3">
          <div class="p-3 rounded-xl bg-blue-50 border border-blue-100">
            <p class="text-2xl font-bold text-blue-600">{{ alignmentData.total_courses }}</p>
            <p class="text-xs text-blue-500 mt-0.5">课程总数</p>
          </div>
          <div class="p-3 rounded-xl bg-emerald-50 border border-emerald-100">
            <p class="text-2xl font-bold text-emerald-600">{{ alignmentData.total_concepts }}</p>
            <p class="text-xs text-emerald-500 mt-0.5">知识点</p>
          </div>
          <div class="p-3 rounded-xl bg-amber-50 border border-amber-100">
            <p class="text-2xl font-bold text-amber-600">{{ alignmentData.total_requirements }}</p>
            <p class="text-xs text-amber-500 mt-0.5">毕业要求</p>
          </div>
        </div>

        <div v-if="alignmentData.gaps.length" class="space-y-2">
          <h4 class="text-sm font-semibold text-red-600 flex items-center gap-1.5">
            <i class="fa-solid fa-triangle-exclamation" />
            知识断层 ({{ alignmentData.gap_count }})
          </h4>
          <div
            v-for="(gap, i) in alignmentData.gaps"
            :key="i"
            class="p-3 rounded-lg border text-xs"
            :class="gap.severity === 'high' ? 'bg-red-50 border-red-200 text-red-700' : 'bg-amber-50 border-amber-200 text-amber-700'"
          >
            <p>{{ gap.suggestion }}</p>
            <div v-if="gap.supporting_courses.length" class="mt-1 flex flex-wrap gap-1">
              <span v-for="c in gap.supporting_courses" :key="c" class="px-1.5 py-0.5 bg-white/60 rounded text-[10px]">{{ c }}</span>
            </div>
          </div>
        </div>

        <div v-if="alignmentData.overlaps.length" class="space-y-2">
          <h4 class="text-sm font-semibold text-amber-600 flex items-center gap-1.5">
            <i class="fa-solid fa-layer-group" />
            知识冗余 ({{ alignmentData.overlap_count }})
          </h4>
          <div
            v-for="(overlap, i) in alignmentData.overlaps"
            :key="i"
            class="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700"
          >
            <p>{{ overlap.suggestion }}</p>
            <div class="mt-1 flex flex-wrap gap-1">
              <span v-for="c in overlap.courses" :key="c" class="px-1.5 py-0.5 bg-white/60 rounded text-[10px]">{{ c }}</span>
            </div>
          </div>
        </div>

        <div v-if="!alignmentData.gaps.length && !alignmentData.overlaps.length" class="text-center py-8">
          <i class="fa-solid fa-check-circle text-emerald-500 text-3xl" />
          <p class="text-sm text-slate-600 mt-2">培养方案一致性良好，未发现明显断层或冗余</p>
        </div>
      </template>
    </div>
  </div>
</template>
