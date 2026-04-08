<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AuthScene from '@/components/AuthScene.vue';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const username = ref('');
const nickname = ref('');
const password = ref('');
const confirmPassword = ref('');
const errorMsg = ref('');

async function handleRegister() {
  errorMsg.value = '';

  if (username.value.length < 3 || username.value.length > 20) {
    errorMsg.value = '用户名长度需保持在 3 到 20 个字符之间';
    return;
  }

  if (password.value.length < 6) {
    errorMsg.value = '密码长度至少需要 6 位';
    return;
  }

  if (password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密码不一致';
    return;
  }

  try {
    await authStore.register(username.value, password.value, nickname.value || undefined);
    router.push('/manual');
  } catch (error: unknown) {
    errorMsg.value = error instanceof Error ? error.message : '注册失败，请稍后重试';
  }
}
</script>

<template>
  <AuthScene
    scene="campus"
    eyebrow="校园 RAG 知识系统"
    headline="创建你的 AI 专业学习入口"
    description="注册后即可保存检索记录、管理个人知识空间，并在人工智能专业场景中持续使用检索增强问答。"
    panel-tag="创建账号"
    title="创建校园账号"
    subtitle="完成基础信息填写后，系统会为你开启专业学习工作台、会话历史和知识空间入口。"
  >
    <form class="auth-form" @submit.prevent="handleRegister">
      <div v-if="errorMsg" class="auth-alert">
        {{ errorMsg }}
      </div>

      <div class="auth-field">
        <label class="auth-label">用户名</label>
        <input v-model="username" type="text" required autocomplete="username" placeholder="请输入用户名（3-20 位）" class="auth-input" />
      </div>

      <div class="auth-field">
        <label class="auth-label">昵称（可选）</label>
        <input v-model="nickname" type="text" autocomplete="nickname" placeholder="给自己设置一个展示昵称" class="auth-input" />
      </div>

      <div class="auth-field">
        <label class="auth-label">密码</label>
        <input v-model="password" type="password" required autocomplete="new-password" placeholder="请输入密码（至少 6 位）" class="auth-input" />
      </div>

      <div class="auth-field">
        <label class="auth-label">确认密码</label>
        <input v-model="confirmPassword" type="password" required autocomplete="new-password" placeholder="请再次输入密码" class="auth-input" />
      </div>

      <button type="submit" :disabled="authStore.isLoading" class="auth-submit">
        {{ authStore.isLoading ? '注册中...' : '创建并进入工作台' }}
      </button>
    </form>

    <p class="auth-footnote">
      已有账号？
      <router-link to="/login" class="auth-link">立即登录</router-link>
    </p>
  </AuthScene>
</template>
