import { VueQueryPlugin, QueryClient, type VueQueryPluginOptions } from '@tanstack/vue-query';

/**
 * 创建 Query Client 实例
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 数据保持新鲜的时间（5分钟）
      staleTime: 5 * 60 * 1000,
      // 缓存时间（10分钟）
      gcTime: 10 * 60 * 1000,
      // 失败重试次数
      retry: 3,
      // 重试延迟（指数退避）
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // 窗口重新获得焦点时重新获取数据
      refetchOnWindowFocus: false,
      // 网络重新连接时重新获取数据
      refetchOnReconnect: true,
    },
    mutations: {
      // 失败重试次数
      retry: 1,
    },
  },
});

/**
 * Vue Query 插件配置
 */
export const vueQueryPluginOptions: VueQueryPluginOptions = {
  queryClient,
  enableDevtoolsV6Plugin: import.meta.env.DEV,
};

export { VueQueryPlugin };
