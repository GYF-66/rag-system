import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';
import './styles/main.css';
import './styles/design-tokens.css';
import './styles/design-system.css';
import './styles/global.css';
import './styles/motion.css';
import { initWebVitals } from './utils/webVitals';
import { vLazyImg } from './directives/lazyImg';
import { vReveal } from './directives/reveal';
import { setupGlobalErrorHandler } from './utils/errorHandler';
import { VueQueryPlugin, vueQueryPluginOptions } from './plugins/vueQuery';
import { useAuthStore } from './stores/auth';
import { useChatStore } from './stores/chat';
import { useHistoryStore } from './stores/history';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
app.use(VueQueryPlugin, vueQueryPluginOptions);

const authStore = useAuthStore(pinia);
if (!authStore.isAuthenticated) {
  useChatStore(pinia).resetGuestSession();
  useHistoryStore(pinia).resetGuestHistory();
}

// 注册全局指令
app.directive('lazy-img', vLazyImg);
app.directive('reveal', vReveal);

// 注册全局错误处理
setupGlobalErrorHandler(app);

app.mount('#app');

// 初始化 Web Vitals 性能指标采集
initWebVitals();
