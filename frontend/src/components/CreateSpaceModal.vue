<script setup lang="ts">
import { ref, computed, watch } from 'vue';

// ============ Props & Emits ============

interface Props {
  show: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  submit: [data: { name: string; description: string; icon: string; color: string }];
  cancel: [];
}>();

// ============ 预设选项 ============

const icons = [
  { id: 'book', class: 'fa-solid fa-book', label: '书籍' },
  { id: 'folder', class: 'fa-solid fa-folder-open', label: '文件夹' },
  { id: 'file', class: 'fa-solid fa-file-lines', label: '文件' },
  { id: 'star', class: 'fa-solid fa-star', label: '收藏' },
  { id: 'lightbulb', class: 'fa-solid fa-lightbulb', label: '灵感' },
  { id: 'rocket', class: 'fa-solid fa-rocket', label: '项目' },
];

const colors = [
  { id: 'emerald', class: 'text-emerald-500', bg: 'bg-emerald-50', label: '绿色' },
  { id: 'indigo', class: 'text-indigo-500', bg: 'bg-indigo-50', label: '靛蓝' },
  { id: 'purple', class: 'text-purple-500', bg: 'bg-purple-50', label: '紫色' },
  { id: 'rose', class: 'text-rose-500', bg: 'bg-rose-50', label: '玫瑰' },
  { id: 'amber', class: 'text-amber-500', bg: 'bg-amber-50', label: '橙色' },
  { id: 'cyan', class: 'text-cyan-500', bg: 'bg-cyan-50', label: '青色' },
];

// ============ 表单数据 ============

const formData = ref({
  name: '',
  description: '',
  icon: icons[0].class,
  color: colors[0].class,
});

const nameError = ref('');

// ============ 验证 ============

const isValidName = computed(() => {
  return formData.value.name.trim().length > 0 && formData.value.name.length <= 20;
});

const validateName = () => {
  if (!formData.value.name.trim()) {
    nameError.value = '请输入空间名称';
    return false;
  }
  if (formData.value.name.length > 20) {
    nameError.value = '名称不能超过20个字符';
    return false;
  }
  nameError.value = '';
  return true;
};

// ============ 选择处理 ============

const selectIcon = (iconClass: string) => {
  formData.value.icon = iconClass;
  console.log('选择图标:', iconClass);
};

const selectColor = (colorClass: string) => {
  formData.value.color = colorClass;
  console.log('选择颜色:', colorClass);
};

// ============ 提交 ============

const handleSubmit = () => {
  console.log('提交表单, formData:', formData.value);
  if (!validateName()) {
    return;
  }

  const data = {
    name: formData.value.name.trim(),
    description: formData.value.description.trim(),
    icon: formData.value.icon,
    color: formData.value.color,
  };

  console.log('emit submit:', data);
  emit('submit', data);

  // 重置表单
  formData.value.name = '';
  formData.value.description = '';
  formData.value.icon = icons[0].class;
  formData.value.color = colors[0].class;
  nameError.value = '';
};

const handleCancel = () => {
  console.log('取消创建');
  emit('cancel');
  // 重置表单
  formData.value.name = '';
  formData.value.description = '';
  formData.value.icon = icons[0].class;
  formData.value.color = colors[0].class;
  nameError.value = '';
};

// ============ 键盘事件 ============

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
  if (e.key === 'Escape') {
    handleCancel();
  }
};

// 监听 show 变化，重置表单
watch(() => props.show, (newVal) => {
  if (!newVal) {
    formData.value.name = '';
    formData.value.description = '';
    formData.value.icon = icons[0].class;
    formData.value.color = colors[0].class;
    nameError.value = '';
  }
});
</script>

<template>
  <!-- Modal 遮罩 -->
  <Transition
    enter-active-class="transition-opacity duration-300"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-200"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      @click="handleCancel"
    >
      <!-- Modal 内容 -->
      <Transition
        enter-active-class="transition-all duration-300"
        enter-from-class="opacity-0 scale-95 translate-y-4"
        enter-to-class="opacity-100 scale-100 translate-y-0"
        leave-active-class="transition-all duration-200"
        leave-from-class="opacity-100 scale-100 translate-y-0"
        leave-to-class="opacity-0 scale-95 translate-y-4"
      >
        <div
          v-if="show"
          class="w-full max-w-md bg-white rounded-2xl shadow-2xl"
          @click.stop
          @keydown="handleKeydown"
          tabindex="-1"
        >
          <!-- 标题 -->
          <div class="px-6 py-5 border-b border-slate-100">
            <h2 class="text-xl font-semibold text-slate-900">创建新空间</h2>
            <p class="text-sm text-slate-500 mt-1">组织和管理您的知识内容</p>
          </div>

          <!-- 表单内容 -->
          <div class="px-6 py-5 space-y-5">
            <!-- 名称输入 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                名称 <span class="text-red-500">*</span>
              </label>
              <input
                v-model="formData.name"
                type="text"
                placeholder="输入空间名称"
                maxlength="20"
                class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-emerald-300 focus:ring-2 focus:ring-emerald-100 outline-none transition-all text-sm"
                :class="nameError ? 'border-red-300 focus:border-red-400 focus:ring-red-100' : ''"
              />
              <div class="flex justify-between mt-1.5">
                <span v-if="nameError" class="text-xs text-red-500">{{ nameError }}</span>
                <span v-else class="text-xs text-slate-400">最多20个字符</span>
                <span class="text-xs text-slate-400">{{ formData.name.length }}/20</span>
              </div>
            </div>

            <!-- 描述输入 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                描述
              </label>
              <textarea
                v-model="formData.description"
                placeholder="添加简短描述（可选）"
                rows="3"
                maxlength="200"
                class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-emerald-300 focus:ring-2 focus:ring-emerald-100 outline-none transition-all text-sm resize-none"
              />
              <div class="flex justify-end mt-1.5">
                <span class="text-xs text-slate-400">{{ formData.description.length }}/200</span>
              </div>
            </div>

            <!-- 图标选择 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                选择图标
              </label>
              <div class="grid grid-cols-6 gap-2">
                <button
                  v-for="icon in icons"
                  :key="icon.id"
                  @click="selectIcon(icon.class)"
                  class="p-3 rounded-xl border-2 transition-all hover:bg-slate-50"
                  :class="formData.icon === icon.class
                    ? 'border-emerald-400 bg-emerald-50'
                    : 'border-slate-200'"
                  :title="icon.label"
                >
                  <i :class="[icon.class, 'text-lg', formData.icon === icon.class ? 'text-emerald-600' : 'text-slate-400']" />
                </button>
              </div>
            </div>

            <!-- 颜色选择 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                选择颜色
              </label>
              <div class="grid grid-cols-6 gap-2">
                <button
                  v-for="color in colors"
                  :key="color.id"
                  @click="selectColor(color.class)"
                  class="p-3 rounded-xl border-2 transition-all"
                  :class="formData.color === color.class
                    ? 'border-emerald-400 bg-emerald-50'
                    : `border-slate-200 ${color.bg}`"
                  :title="color.label"
                >
                  <div
                    class="w-5 h-5 rounded-full mx-auto"
                    :class="formData.color === color.class ? color.class : 'bg-slate-300'"
                  />
                </button>
              </div>
            </div>
          </div>

          <!-- 底部按钮 -->
          <div class="px-6 py-4 bg-slate-50 rounded-b-2xl flex items-center justify-end space-x-3">
            <button
              @click="handleCancel"
              class="px-5 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 hover:border-slate-300 transition-all"
            >
              取消
            </button>
            <button
              @click="handleSubmit"
              :disabled="!isValidName"
              class="px-5 py-2 text-sm font-medium text-white bg-gradient-to-r from-emerald-500 to-indigo-500 rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none"
            >
              创建空间
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
/* 确保滚动条样式 */
:deep(textarea::-webkit-scrollbar) {
  width: 4px;
}

:deep(textarea::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(textarea::-webkit-scrollbar-thumb) {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
}

:deep(textarea::-webkit-scrollbar-thumb:hover) {
  background: rgba(0, 0, 0, 0.16);
}
</style>