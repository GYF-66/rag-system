<script setup lang="ts">
import { useSlots } from 'vue';
import LibraryBackdrop from '@/components/LibraryBackdrop.vue';

interface MastheadStat {
  label: string;
  value: string;
}

interface Props {
  eyebrow: string;
  title: string;
  description: string;
  icon?: string;
  pills?: string[];
  stats?: MastheadStat[];
  intensity?: 'low' | 'medium' | 'high';
}

withDefaults(defineProps<Props>(), {
  icon: 'fa-solid fa-landmark',
  pills: () => [],
  stats: () => [],
  intensity: 'medium',
});

const slots = useSlots();
</script>

<template>
  <LibraryBackdrop variant="compact" :interactive="false" :intensity="intensity" class="library-masthead">
    <div class="library-masthead__shell">
      <div class="library-masthead__copy reveal-item is-revealed">
        <p class="library-masthead__eyebrow">{{ eyebrow }}</p>
        <div class="library-masthead__headline">
          <span class="library-masthead__icon"><i :class="icon" /></span>
          <h1>{{ title }}</h1>
        </div>
        <p class="library-masthead__description">{{ description }}</p>

        <div v-if="pills.length" class="library-masthead__pills">
          <span v-for="pill in pills" :key="pill" class="library-masthead__pill magnetic-card">{{ pill }}</span>
        </div>

        <div v-if="stats.length" class="library-masthead__stats">
          <article v-for="stat in stats" :key="stat.label" class="library-masthead__stat glow-hover">
            <strong>{{ stat.value }}</strong>
            <span>{{ stat.label }}</span>
          </article>
        </div>
      </div>

      <aside v-if="slots.aside" class="library-masthead__aside reveal-item is-revealed" style="--reveal-delay: 140ms">
        <slot name="aside" />
      </aside>
    </div>
  </LibraryBackdrop>
</template>

<style scoped>
.library-masthead {
  box-shadow: 0 28px 84px rgba(78, 56, 42, 0.14);
}

.library-masthead__shell {
  display: grid;
  gap: 1.5rem;
  min-height: 320px;
  padding: 2rem;
  align-items: end;
}

.library-masthead__copy {
  max-width: 54rem;
  padding: 1.25rem 1.25rem 0;
}

.library-masthead__eyebrow {
  color: rgba(75, 48, 34, 0.78);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.library-masthead__headline {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 0.9rem;
}

.library-masthead__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 1.1rem;
  color: #fff7ee;
  background: linear-gradient(135deg, rgba(148, 75, 48, 0.96), rgba(198, 132, 83, 0.92));
  box-shadow: 0 18px 32px rgba(118, 63, 41, 0.22);
}

.library-masthead__headline h1 {
  font-size: clamp(1.95rem, 3vw, 3.15rem);
  font-weight: 900;
  line-height: 1.05;
  color: #241918;
}

.library-masthead__description {
  margin-top: 1rem;
  max-width: 46rem;
  color: rgba(52, 37, 32, 0.78);
  font-size: 1rem;
  line-height: 1.8;
}

.library-masthead__pills,
.library-masthead__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.library-masthead__pill,
.library-masthead__stat {
  border: 1px solid rgba(120, 85, 63, 0.18);
  background: rgba(255, 251, 245, 0.84);
  backdrop-filter: blur(12px);
}

.library-masthead__pill {
  padding: 0.65rem 1rem;
  border-radius: 999px;
  color: rgba(73, 51, 40, 0.88);
  font-size: 0.82rem;
  font-weight: 600;
}

.library-masthead__stat {
  display: grid;
  min-width: 132px;
  padding: 0.85rem 1rem;
  border-radius: 1.1rem;
  box-shadow: 0 12px 32px rgba(61, 39, 29, 0.08);
}

.library-masthead__stat strong {
  color: #2f231f;
  font-size: 1rem;
}

.library-masthead__stat span {
  margin-top: 0.2rem;
  color: rgba(94, 73, 63, 0.74);
  font-size: 0.78rem;
}

.library-masthead__aside {
  align-self: stretch;
  justify-self: end;
  width: min(100%, 320px);
  padding: 1.2rem;
  border-radius: 1.5rem;
  border: 1px solid rgba(120, 85, 63, 0.18);
  background: rgba(39, 24, 18, 0.8);
  backdrop-filter: blur(18px);
  color: #fef8f2;
  box-shadow: 0 24px 64px rgba(25, 15, 11, 0.24);
}

@media (min-width: 1024px) {
  .library-masthead__shell {
    grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
  }
}

@media (max-width: 768px) {
  .library-masthead__shell {
    padding: 1.2rem;
  }

  .library-masthead__copy {
    padding: 0.6rem 0.4rem 0;
  }

  .library-masthead__headline {
    align-items: flex-start;
  }
}
</style>
