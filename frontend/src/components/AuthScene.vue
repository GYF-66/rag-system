<script setup lang="ts">
import LibraryBackdrop from '@/components/LibraryBackdrop.vue';

interface AuthSceneProps {
  eyebrow: string;
  headline: string;
  description: string;
  panelTag: string;
  title: string;
  subtitle: string;
  scene?: 'default' | 'campus';
}

withDefaults(defineProps<AuthSceneProps>(), {
  scene: 'campus',
});

const authHighlights = [
  { title: '检索增强问答', description: '围绕 RAG 主链路组织专业资料、来源片段和检索解释。' },
  { title: '专业知识场景', description: '聚焦人工智能专业培养方案、课程体系、实践与学习支持。' },
  { title: '连续学习入口', description: '登录后衔接历史记录、知识空间与持续提问体验。' },
];
</script>

<template>
  <LibraryBackdrop variant="auth" intensity="high" class="auth-shell">
    <div class="auth-shell__layout">
      <section class="auth-shell__intro reveal-item is-revealed">
        <div class="auth-shell__brand magnetic-card">
          <div class="auth-shell__brand-mark">
            <img src="/校徽.jpg" alt="安徽信息工程学院校徽" class="auth-shell__brand-emblem" />
          </div>
          <div>
            <p class="auth-shell__brand-title">安信工 AI 专业学习工作台</p>
            <p class="auth-shell__brand-subtitle">以教学任务场景承载专业知识问答与检索链路</p>
          </div>
        </div>

        <div class="auth-shell__copy">
          <p class="auth-shell__eyebrow">{{ eyebrow }}</p>
          <h1>{{ headline }}</h1>
          <p class="auth-shell__description">{{ description }}</p>
        </div>

        <div class="auth-shell__stats stagger-grid">
          <article class="glow-hover" v-reveal="60">
            <strong>RAG First</strong>
            <span>先检索、后生成、保留来源</span>
          </article>
          <article class="glow-hover" v-reveal="120">
            <strong>校园语料</strong>
            <span>课程、培养方案与学习支持统一组织</span>
          </article>
          <article class="glow-hover" v-reveal="180">
            <strong>连续体验</strong>
            <span>从首页搜索到工作台问答无缝衔接</span>
          </article>
        </div>

        <div class="auth-shell__highlights stagger-grid">
          <article v-for="(item, index) in authHighlights" :key="item.title" class="glow-hover" v-reveal="240 + index * 80">
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
          </article>
        </div>
      </section>

      <section class="auth-shell__panel reveal-item is-revealed" style="--reveal-delay: 120ms">
        <div class="auth-shell__panel-sheen" aria-hidden="true"></div>
        <div class="auth-shell__panel-inner">
          <div class="auth-shell__panel-head">
            <span class="auth-shell__panel-tag">{{ panelTag }}</span>
            <h2>{{ title }}</h2>
            <p>{{ subtitle }}</p>
          </div>

          <slot />
        </div>
      </section>
    </div>
  </LibraryBackdrop>
</template>

<style scoped>
.auth-shell {
  color: #2c221e;
}

.auth-shell__layout {
  position: relative;
  z-index: 2;
  display: grid;
  gap: 2rem;
  min-height: 100dvh;
  max-width: 1320px;
  margin: 0 auto;
  padding: 1.4rem;
  align-items: center;
}

.auth-shell__intro,
.auth-shell__panel {
  position: relative;
}

.auth-shell__intro {
  padding: 1.2rem 0.8rem;
}

.auth-shell__brand {
  display: inline-flex;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(118, 82, 59, 0.18);
  background: rgba(255, 250, 244, 0.74);
  backdrop-filter: blur(14px);
  box-shadow: 0 16px 48px rgba(73, 47, 35, 0.1);
}

.auth-shell__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3.35rem;
  height: 3.35rem;
  overflow: hidden;
  border-radius: 1.15rem;
  border: 1px solid rgba(118, 82, 59, 0.18);
  background: rgba(255, 255, 255, 0.88);
}

.auth-shell__brand-emblem {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.auth-shell__brand-title {
  font-size: 0.98rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.auth-shell__brand-subtitle {
  margin-top: 0.2rem;
  color: rgba(83, 61, 50, 0.72);
  font-size: 0.8rem;
}

.auth-shell__copy {
  margin-top: 2rem;
  max-width: 42rem;
}

.auth-shell__eyebrow {
  color: rgba(103, 64, 43, 0.88);
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.auth-shell__copy h1 {
  margin-top: 1rem;
  color: #231816;
  font-size: clamp(2.8rem, 5vw, 4.8rem);
  font-weight: 900;
  line-height: 1.02;
  letter-spacing: -0.04em;
}

.auth-shell__description {
  margin-top: 1rem;
  max-width: 38rem;
  color: rgba(61, 41, 35, 0.8);
  font-size: 1.08rem;
  line-height: 1.9;
}

.auth-shell__stats,
.auth-shell__highlights {
  display: grid;
  gap: 0.9rem;
  margin-top: 1.6rem;
}

.auth-shell__stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.auth-shell__stats article,
.auth-shell__highlights article {
  padding: 1rem 1.1rem;
  border-radius: 1.35rem;
  border: 1px solid rgba(118, 82, 59, 0.16);
  background: rgba(255, 250, 244, 0.76);
  backdrop-filter: blur(14px);
  box-shadow: 0 18px 42px rgba(73, 47, 35, 0.09);
}

.auth-shell__stats strong,
.auth-shell__highlights strong {
  display: block;
  color: #2e211d;
  font-size: 0.92rem;
  font-weight: 800;
}

.auth-shell__stats span,
.auth-shell__highlights p {
  display: block;
  margin-top: 0.35rem;
  color: rgba(80, 59, 48, 0.76);
  font-size: 0.84rem;
  line-height: 1.7;
}

.auth-shell__panel {
  border-radius: 2rem;
  border: 1px solid rgba(118, 82, 59, 0.18);
  background: rgba(255, 251, 247, 0.92);
  backdrop-filter: blur(22px) saturate(140%);
  box-shadow: 0 32px 84px rgba(41, 26, 19, 0.22);
  overflow: hidden;
}

.auth-shell__panel-sheen {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.54), transparent 38%, rgba(174, 92, 63, 0.08));
  pointer-events: none;
}

.auth-shell__panel-inner {
  position: relative;
  z-index: 1;
  padding: 1.8rem;
}

.auth-shell__panel-head {
  margin-bottom: 1.4rem;
}

.auth-shell__panel-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  color: #8a412b;
  background: rgba(174, 92, 63, 0.12);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.auth-shell__panel-head h2 {
  margin-top: 0.95rem;
  color: #261a18;
  font-size: clamp(1.75rem, 3vw, 2.2rem);
  font-weight: 900;
}

.auth-shell__panel-head p {
  margin-top: 0.55rem;
  color: rgba(81, 59, 48, 0.78);
  font-size: 0.96rem;
  line-height: 1.8;
}

:deep(.auth-form) {
  display: grid;
  gap: 1rem;
}

:deep(.auth-field) {
  display: grid;
  gap: 0.5rem;
}

:deep(.auth-label) {
  color: #47342d;
  font-size: 0.84rem;
  font-weight: 700;
}

:deep(.auth-input) {
  width: 100%;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
  border: 1px solid rgba(118, 82, 59, 0.16);
  background: rgba(255, 255, 255, 0.88);
  color: #2b201c;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

:deep(.auth-input:focus) {
  border-color: rgba(154, 82, 56, 0.44);
  box-shadow: 0 0 0 5px rgba(174, 92, 63, 0.12);
  transform: translateY(-1px);
}

:deep(.auth-alert) {
  padding: 0.95rem 1rem;
  border-radius: 1rem;
  border: 1px solid rgba(180, 82, 67, 0.2);
  background: rgba(252, 238, 236, 0.92);
  color: #a14333;
  font-size: 0.88rem;
}

:deep(.auth-submit) {
  width: 100%;
  padding: 1rem 1.1rem;
  border: none;
  border-radius: 1.05rem;
  color: #fff9f4;
  background: linear-gradient(135deg, #944b30 0%, #c68453 100%);
  font-size: 0.96rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: transform 180ms ease, box-shadow 180ms ease, opacity 180ms ease;
  box-shadow: 0 20px 40px rgba(148, 75, 48, 0.2);
}

:deep(.auth-submit:hover:not(:disabled)) {
  transform: translateY(-1px);
}

:deep(.auth-submit:disabled) {
  cursor: not-allowed;
  opacity: 0.72;
}

:deep(.auth-footnote) {
  margin-top: 1rem;
  color: rgba(80, 59, 48, 0.78);
  font-size: 0.88rem;
  text-align: center;
}

:deep(.auth-link),
:deep(.auth-secondary-link) {
  color: #8d4a30;
  font-weight: 700;
  text-decoration: none;
}

:deep(.auth-link:hover),
:deep(.auth-secondary-link:hover) {
  color: #6d3725;
}

:deep(.auth-secondary-action) {
  margin-top: 0.65rem;
  text-align: center;
}

@media (min-width: 1120px) {
  .auth-shell__layout {
    grid-template-columns: minmax(0, 1.1fr) minmax(420px, 500px);
    gap: 2.4rem;
    padding: 2rem;
  }
}

@media (max-width: 860px) {
  .auth-shell__layout {
    padding: 1rem;
  }

  .auth-shell__intro {
    padding: 0.5rem 0.2rem;
  }

  .auth-shell__stats {
    grid-template-columns: 1fr;
  }
}
</style>
