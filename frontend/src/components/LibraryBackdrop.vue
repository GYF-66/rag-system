<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

type LibraryBackdropVariant = 'hero' | 'auth' | 'compact' | 'page';
type LibraryBackdropIntensity = 'low' | 'medium' | 'high';

interface Props {
  variant?: LibraryBackdropVariant;
  interactive?: boolean;
  intensity?: LibraryBackdropIntensity;
  scrollReactive?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'hero',
  interactive: true,
  intensity: 'medium',
  scrollReactive: true,
});

const pointerX = ref(50);
const pointerY = ref(36);
const scrollDepth = ref(0);

let animationFrameId: number | null = null;
let pendingX = pointerX.value;
let pendingY = pointerY.value;

const intensityMap: Record<LibraryBackdropIntensity, number> = {
  low: 0.5,
  medium: 0.85,
  high: 1.18,
};

const sceneStyle = computed(() => ({
  '--scene-strength': `${intensityMap[props.intensity]}`,
  '--scene-x-soft': `${(pointerX.value - 50) * 0.18 * intensityMap[props.intensity]}px`,
  '--scene-y-soft': `${((pointerY.value - 50) * 0.12 + scrollDepth.value * 0.35) * intensityMap[props.intensity]}px`,
  '--scene-x-base': `${(pointerX.value - 50) * 0.28 * intensityMap[props.intensity]}px`,
  '--scene-y-base': `${((pointerY.value - 50) * 0.18 + scrollDepth.value * 0.6) * intensityMap[props.intensity]}px`,
  '--scene-x-deep': `${(pointerX.value - 50) * 0.4 * intensityMap[props.intensity]}px`,
  '--scene-y-deep': `${((pointerY.value - 50) * 0.24 + scrollDepth.value) * intensityMap[props.intensity]}px`,
  '--pointer-x': `${pointerX.value}%`,
  '--pointer-y': `${pointerY.value}%`,
  '--scene-scroll': `${scrollDepth.value}px`,
}));

function clamp(value: number) {
  return Math.min(100, Math.max(0, value));
}

function commitPointer() {
  animationFrameId = window.requestAnimationFrame(() => {
    pointerX.value = pendingX;
    pointerY.value = pendingY;
    animationFrameId = null;
  });
}

function schedulePointerCommit() {
  if (animationFrameId !== null) {
    return;
  }

  commitPointer();
}

function handlePointerMove(event: PointerEvent) {
  if (!props.interactive) {
    return;
  }

  const currentTarget = event.currentTarget as HTMLElement | null;
  if (!currentTarget) {
    return;
  }

  const rect = currentTarget.getBoundingClientRect();
  pendingX = clamp(((event.clientX - rect.left) / rect.width) * 100);
  pendingY = clamp(((event.clientY - rect.top) / rect.height) * 100);
  schedulePointerCommit();
}

function resetPointer() {
  if (!props.interactive) {
    return;
  }

  pendingX = 50;
  pendingY = 36;
  schedulePointerCommit();
}

function updateScrollDepth() {
  if (!props.scrollReactive) {
    scrollDepth.value = 0;
    return;
  }

  const nextDepth = Math.min(window.scrollY * 0.04, 18);
  scrollDepth.value = Number(nextDepth.toFixed(2));
}

onMounted(() => {
  updateScrollDepth();
  if (props.scrollReactive) {
    window.addEventListener('scroll', updateScrollDepth, { passive: true });
  }
});

onBeforeUnmount(() => {
  if (animationFrameId !== null) {
    window.cancelAnimationFrame(animationFrameId);
  }
  if (props.scrollReactive) {
    window.removeEventListener('scroll', updateScrollDepth);
  }
});
</script>

<template>
  <section
    class="library-scene"
    :class="[
      `library-scene--${variant}`,
      `library-scene--${intensity}`,
      { 'library-scene--interactive': interactive, 'library-scene--scroll-reactive': scrollReactive },
    ]"
    :style="sceneStyle"
    @pointermove="handlePointerMove"
    @pointerleave="resetPointer"
  >
    <div class="library-scene__art" aria-hidden="true">
      <div class="library-scene__cloud library-scene__cloud--one"></div>
      <div class="library-scene__cloud library-scene__cloud--two"></div>
      <div class="library-scene__cloud library-scene__cloud--three"></div>
      <div class="library-scene__light"></div>
      <div class="library-scene__mist"></div>
      <div class="library-scene__wash"></div>
      <div class="library-scene__grain"></div>
      <div class="library-scene__bloom"></div>

      <svg
        class="library-scene__svg"
        viewBox="0 0 1600 920"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <linearGradient id="librarySky" x1="800" y1="40" x2="800" y2="640" gradientUnits="userSpaceOnUse">
            <stop offset="0" stop-color="#AFCBE2" />
            <stop offset="0.35" stop-color="#C6D6E7" />
            <stop offset="0.7" stop-color="#F0E7D7" />
            <stop offset="1" stop-color="#F6EFE6" />
          </linearGradient>
          <radialGradient id="libraryGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(806 168) rotate(90) scale(188 344)">
            <stop offset="0" stop-color="#FFFCEB" stop-opacity="0.96" />
            <stop offset="1" stop-color="#FFFCEB" stop-opacity="0" />
          </radialGradient>
          <linearGradient id="libraryRoad" x1="800" y1="778" x2="800" y2="920" gradientUnits="userSpaceOnUse">
            <stop offset="0" stop-color="#7A7473" />
            <stop offset="1" stop-color="#5C5756" />
          </linearGradient>
          <linearGradient id="libraryLawn" x1="800" y1="560" x2="800" y2="790" gradientUnits="userSpaceOnUse">
            <stop offset="0" stop-color="#A7C96A" />
            <stop offset="1" stop-color="#6F9A3D" />
          </linearGradient>
          <linearGradient id="libraryFacade" x1="800" y1="154" x2="800" y2="612" gradientUnits="userSpaceOnUse">
            <stop offset="0" stop-color="#F2E7D8" />
            <stop offset="1" stop-color="#D6C9B8" />
          </linearGradient>
          <linearGradient id="librarySide" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#D8CBB9" />
            <stop offset="1" stop-color="#C0B39F" />
          </linearGradient>
          <linearGradient id="windowTone" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#7C848A" stop-opacity="0.78" />
            <stop offset="1" stop-color="#596168" stop-opacity="0.92" />
          </linearGradient>
          <linearGradient id="canopyTone" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#C9B856" />
            <stop offset="1" stop-color="#87A34B" />
          </linearGradient>
          <pattern id="windowGrid" width="18" height="20" patternUnits="userSpaceOnUse">
            <rect width="18" height="20" fill="transparent" />
            <rect x="5" y="0" width="2.8" height="20" fill="url(#windowTone)" />
            <rect x="0" y="9" width="18" height="1.1" fill="#AEB4B8" fill-opacity="0.3" />
          </pattern>
          <filter id="sceneShadow" x="350" y="90" width="900" height="620" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
            <feDropShadow dx="0" dy="28" stdDeviation="28" flood-color="#6D584D" flood-opacity="0.18" />
          </filter>
        </defs>

        <rect width="1600" height="920" fill="url(#librarySky)" />
        <ellipse class="library-scene__sun" cx="806" cy="162" rx="352" ry="196" fill="url(#libraryGlow)" />

        <g class="library-scene__clouds library-scene__clouds--back">
          <path d="M280 102C426 92 564 102 694 132C784 154 878 162 980 160C1100 158 1217 174 1334 212" stroke="#F2E0D5" stroke-opacity="0.58" stroke-width="48" stroke-linecap="round" />
          <path d="M180 182C310 176 452 188 606 222C720 248 838 256 958 248C1082 240 1206 252 1336 286" stroke="#F3E8DD" stroke-opacity="0.48" stroke-width="34" stroke-linecap="round" />
        </g>

        <g class="library-scene__side-buildings">
          <path d="M0 294L126 244L188 262V620H0V294Z" fill="#47484F" fill-opacity="0.94" />
          <rect x="24" y="306" width="124" height="260" fill="#545660" fill-opacity="0.52" />
          <path d="M1600 294L1474 244L1412 262V620H1600V294Z" fill="#47484F" fill-opacity="0.94" />
          <rect x="1452" y="306" width="124" height="260" fill="#545660" fill-opacity="0.52" />
        </g>

        <path d="M0 610C260 582 532 568 804 568C1088 568 1356 586 1600 624V790H0V610Z" fill="url(#libraryLawn)" />
        <rect x="0" y="786" width="1600" height="134" fill="url(#libraryRoad)" />
        <rect x="0" y="748" width="1600" height="38" fill="#DBD1C5" />

        <g class="library-scene__tree-line library-scene__tree-line--left">
          <g v-for="index in 9" :key="`left-tree-${index}`" :style="{ transform: `translate(${66 + (index - 1) * 52}px, ${0}px)` }">
            <rect x="0" y="548" width="4" height="112" fill="#7B624A" />
            <circle cx="2" cy="536" r="18" fill="url(#canopyTone)" />
            <circle cx="14" cy="530" r="14" fill="#B2BF57" />
            <circle cx="-10" cy="530" r="13" fill="#97AC4F" />
          </g>
        </g>

        <g class="library-scene__tree-line library-scene__tree-line--right">
          <g v-for="index in 9" :key="`right-tree-${index}`" :style="{ transform: `translate(${1134 + (index - 1) * 52}px, ${0}px)` }">
            <rect x="0" y="548" width="4" height="112" fill="#7B624A" />
            <circle cx="2" cy="536" r="18" fill="url(#canopyTone)" />
            <circle cx="14" cy="530" r="14" fill="#B2BF57" />
            <circle cx="-10" cy="530" r="13" fill="#97AC4F" />
          </g>
        </g>

        <g class="library-scene__building" filter="url(#sceneShadow)">
          <rect x="560" y="454" width="482" height="158" fill="url(#libraryFacade)" />
          <rect x="560" y="454" width="482" height="118" fill="url(#windowGrid)" opacity="0.9" />
          <rect x="550" y="440" width="502" height="22" fill="#E8DDCF" />

          <rect x="492" y="336" width="628" height="118" fill="url(#libraryFacade)" />
          <rect x="492" y="336" width="628" height="88" fill="url(#windowGrid)" opacity="0.9" />
          <rect x="482" y="324" width="648" height="20" fill="#E7DCCD" />

          <rect x="624" y="236" width="372" height="102" fill="url(#libraryFacade)" />
          <rect x="624" y="236" width="372" height="76" fill="url(#windowGrid)" opacity="0.92" />
          <rect x="614" y="224" width="392" height="18" fill="#E9DFD1" />

          <rect x="654" y="160" width="316" height="62" stroke="#E7D7C5" stroke-width="10" />
          <path d="M674 182H950" stroke="#E8DCCF" stroke-width="8" stroke-linecap="round" />

          <rect x="706" y="394" width="190" height="30" fill="#C6B7A4" opacity="0.62" />
          <rect x="732" y="424" width="138" height="30" fill="#8A9BA8" opacity="0.86" />

          <g class="library-scene__columns">
            <rect x="642" y="560" width="20" height="52" fill="#E4D6C3" />
            <rect x="726" y="560" width="20" height="52" fill="#E4D6C3" />
            <rect x="810" y="560" width="20" height="52" fill="#E4D6C3" />
            <rect x="894" y="560" width="20" height="52" fill="#E4D6C3" />
          </g>
        </g>

        <g class="library-scene__sign">
          <rect x="660" y="670" width="284" height="16" rx="8" fill="#7A5A49" fill-opacity="0.44" />
          <rect x="664" y="652" width="272" height="20" rx="10" fill="#ECE4D8" />
          <text x="716" y="668" fill="#FFFFFF" font-size="46" font-weight="800" text-anchor="middle">I</text>
          <text x="770" y="668" fill="#E34D44" font-size="44" font-weight="900" text-anchor="middle">❤</text>
          <text x="868" y="668" fill="#FFFFFF" font-size="46" font-weight="800" text-anchor="middle">AIIT</text>
        </g>
      </svg>

    </div>

    <div class="library-scene__content">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.library-scene {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(circle at top, rgba(255, 249, 239, 0.68), transparent 42%),
    linear-gradient(180deg, #f6efe6 0%, #efe6db 100%);
}

.library-scene--low {
  --scene-cloud-opacity: 0.24;
  --scene-bloom-opacity: 0.34;
}

.library-scene--medium {
  --scene-cloud-opacity: 0.34;
  --scene-bloom-opacity: 0.42;
}

.library-scene--high {
  --scene-cloud-opacity: 0.46;
  --scene-bloom-opacity: 0.56;
}

.library-scene--hero {
  min-height: 72vh;
}

.library-scene--auth {
  min-height: 100dvh;
}

.library-scene--compact {
  min-height: 320px;
  border-radius: 32px;
}

.library-scene--page {
  min-height: 260px;
  border-radius: 28px;
}

.library-scene__art,
.library-scene__content {
  position: relative;
  z-index: 1;
}

.library-scene__art {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.library-scene__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transform: translate3d(var(--scene-x-soft), var(--scene-y-soft), 0) scale(1.03);
  transform-origin: center;
}

.library-scene__light,
.library-scene__mist,
.library-scene__bloom,
.library-scene__wash,
.library-scene__grain {
  position: absolute;
  inset: 0;
}

.library-scene__cloud {
  position: absolute;
  border-radius: 999px;
  background: radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 0.74), rgba(255, 255, 255, 0.08) 72%, transparent 100%);
  opacity: var(--scene-cloud-opacity, 0.34);
  filter: blur(10px);
  mix-blend-mode: screen;
  animation: cloud-drift var(--motion-duration-cloud, 24s) linear infinite alternate;
}

.library-scene__cloud--one {
  top: 10%;
  left: 8%;
  width: 220px;
  height: 74px;
}

.library-scene__cloud--two {
  top: 16%;
  right: 12%;
  width: 280px;
  height: 96px;
  animation-duration: calc(var(--motion-duration-cloud, 24s) * 1.2);
}

.library-scene__cloud--three {
  top: 22%;
  left: 28%;
  width: 180px;
  height: 64px;
  animation-duration: calc(var(--motion-duration-cloud, 24s) * 0.85);
}

.library-scene__light {
  background:
    radial-gradient(circle at var(--pointer-x) var(--pointer-y), rgba(255, 252, 236, 0.26), transparent 18%),
    radial-gradient(circle at 50% 16%, rgba(255, 247, 226, 0.56), transparent 34%);
  mix-blend-mode: screen;
}

.library-scene__mist {
  background:
    linear-gradient(180deg, rgba(245, 239, 231, 0.12) 0%, rgba(244, 236, 226, 0.18) 46%, rgba(244, 236, 226, 0.72) 100%),
    radial-gradient(circle at 50% 72%, rgba(255, 255, 255, 0.18), transparent 30%);
}

.library-scene__bloom {
  background:
    radial-gradient(circle at 50% 22%, rgba(255, 246, 220, 0.52), transparent 26%),
    radial-gradient(circle at 54% 68%, rgba(255, 255, 255, 0.18), transparent 30%);
  opacity: var(--scene-bloom-opacity, 0.4);
  mix-blend-mode: screen;
  animation: glow-pulse var(--motion-duration-glow, 6s) ease-in-out infinite alternate;
}

.library-scene__wash {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.1), transparent 20%, transparent 72%, rgba(46, 28, 18, 0.18)),
    linear-gradient(90deg, rgba(37, 28, 20, 0.08), transparent 18%, transparent 82%, rgba(37, 28, 20, 0.08));
}

.library-scene__grain {
  opacity: 0.08;
  background-image:
    radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.6) 0 1px, transparent 1px),
    radial-gradient(circle at 80% 30%, rgba(76, 56, 43, 0.45) 0 0.8px, transparent 0.8px),
    radial-gradient(circle at 40% 80%, rgba(255, 255, 255, 0.55) 0 1px, transparent 1px);
  background-size: 90px 90px, 130px 130px, 110px 110px;
  mix-blend-mode: soft-light;
}

.library-scene__content {
  position: relative;
  z-index: 2;
}

.library-scene__building {
  transform: translate3d(var(--scene-x-base), var(--scene-y-base), 0);
}

.library-scene__side-buildings {
  transform: translate3d(var(--scene-x-deep), calc(var(--scene-y-deep) * 0.6), 0);
}

.library-scene__tree-line--left {
  transform: translate3d(calc(var(--scene-x-deep) * -1), 0, 0);
}

.library-scene__tree-line--right {
  transform: translate3d(var(--scene-x-deep), 0, 0);
}

.library-scene__tree-line g {
  transform-box: fill-box;
  transform-origin: center bottom;
  animation: tree-sway var(--motion-duration-tree, 7s) ease-in-out infinite alternate;
}

.library-scene__tree-line g:nth-child(2n) {
  animation-duration: 7.2s;
}

.library-scene__tree-line g:nth-child(3n) {
  animation-duration: 5.5s;
}

.library-scene__clouds {
  animation: cloud-drift var(--motion-duration-cloud, 24s) linear infinite alternate;
}

.library-scene__clouds--back {
  transform: translate3d(var(--scene-x-soft), 0, 0);
}

.library-scene__sun {
  animation: glow-pulse calc(var(--motion-duration-glow, 6s) + 2s) ease-in-out infinite alternate;
}

.library-scene__sign {
  animation: sign-float calc(var(--motion-duration-glow, 6s) * 0.9) ease-in-out infinite;
}

.library-scene__columns {
  animation: column-glow calc(var(--motion-duration-glow, 6s) * 0.8) ease-in-out infinite alternate;
}

.library-scene--scroll-reactive .library-scene__art {
  transform: translate3d(0, calc(var(--scene-scroll) * -0.08), 0);
}

.library-scene--compact .library-scene__svg,
.library-scene--page .library-scene__svg {
  transform: translate3d(var(--scene-x-soft), calc(var(--scene-y-soft) * 0.6), 0) scale(1.08);
}

.library-scene--compact .library-scene__mist,
.library-scene--page .library-scene__mist {
  background:
    linear-gradient(180deg, rgba(245, 239, 231, 0.05) 0%, rgba(244, 236, 226, 0.12) 42%, rgba(244, 236, 226, 0.76) 100%),
    radial-gradient(circle at 50% 74%, rgba(255, 255, 255, 0.12), transparent 32%);
}

.library-scene--compact .library-scene__cloud,
.library-scene--page .library-scene__cloud {
  opacity: calc(var(--scene-cloud-opacity, 0.34) * 0.66);
}

@media (max-width: 768px) {
  .library-scene__cloud--three {
    display: none;
  }

  .library-scene__cloud--one {
    width: 148px;
    height: 54px;
  }

  .library-scene__cloud--two {
    width: 188px;
    height: 64px;
  }
}

@keyframes cloud-drift {
  0% {
    transform: translate3d(-12px, 0, 0);
  }
  100% {
    transform: translate3d(16px, -6px, 0);
  }
}

@keyframes tree-sway {
  0% {
    transform: rotate(-1.8deg) translateY(0);
  }
  100% {
    transform: rotate(1.6deg) translateY(-3px);
  }
}

@keyframes glow-pulse {
  0% {
    opacity: 0.88;
  }
  100% {
    opacity: 1;
  }
}

@keyframes sign-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

@keyframes column-glow {
  0% {
    opacity: 0.8;
  }
  100% {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .library-scene__cloud,
  .library-scene__clouds,
  .library-scene__tree-line g,
  .library-scene__sun,
  .library-scene__sign,
  .library-scene__columns,
  .library-scene__bloom {
    animation: none;
  }

  .library-scene__svg,
  .library-scene__building,
  .library-scene__side-buildings,
  .library-scene__tree-line--left,
  .library-scene__tree-line--right {
    transform: none;
  }
}
</style>
