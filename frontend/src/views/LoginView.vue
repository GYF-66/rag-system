<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AuthScene from '@/components/AuthScene.vue';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const username = ref('');
const password = ref('');
const errorMsg = ref('');

async function handleLogin() {
  errorMsg.value = '';

  try {
    await authStore.login(username.value, password.value);
    router.push('/manual');
  } catch (error: unknown) {
    errorMsg.value = error instanceof Error ? error.message : '登录失败，请稍后重试';
  }
}
</script>

<template>
  <AuthScene
    scene="campus"
    eyebrow="校园 RAG 知识系统"
    headline="进入 AI 专业学习入口"
    description="围绕人工智能专业培养方案、课程体系、来源追踪问答与个人学习记录，统一进入校园知识工作流。"
    panel-tag="安全登录"
    title="欢迎回来"
    subtitle="登录后继续使用工作台、会话历史与知识空间，延续你的检索、提问与来源核验。"
  >
    <form class="auth-form" @submit.prevent="handleLogin">
      <div v-if="errorMsg" class="auth-alert">
        {{ errorMsg }}
      </div>

      <div class="auth-field">
        <label class="auth-label">用户名</label>
        <input v-model="username" type="text" required autocomplete="username" placeholder="请输入你的校园账号用户名" class="auth-input" />
      </div>

      <div class="auth-field">
        <label class="auth-label">密码</label>
        <input v-model="password" type="password" required autocomplete="current-password" placeholder="请输入登录密码" class="auth-input" />
      </div>

      <button type="submit" :disabled="authStore.isLoading" class="auth-submit">
        {{ authStore.isLoading ? '登录中...' : '进入专业学习工作台' }}
      </button>
    </form>

    <p class="auth-footnote">
      还没有账号？
      <router-link to="/register" class="auth-link">立即注册</router-link>
    </p>

    <div class="auth-secondary-action">
      <router-link to="/manual" class="auth-secondary-link">先进入公开问答体验</router-link>
    </div>
  </AuthScene>
</template>
