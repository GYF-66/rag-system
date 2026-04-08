/**
 * 组件类型定义
 */

/**
 * 侧边栏菜单项
 */
export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  badge?: string;
  active?: boolean;
  shortcut?: string;
  group?: string;
}

/**
 * 用户信息
 */
export interface UserInfo {
  name: string;
  email: string;
  avatar: string;
}

/**
 * 快速启动项
 */
export interface QuickAction {
  id: string;
  emoji: string;
  label: string;
  query: string;
}

/**
 * 导航项
 */
export interface NavItem {
  id: string;
  label: string;
  icon: string;
}

/**
 * 搜索结果
 */
export interface SearchResult {
  id: string;
  title: string;
  content: string;
  source: string;
  relevance: number;
}