<script setup>
import {computed, ref} from 'vue'
import SvgIcon from "@/components/SvgIcon/index.vue";
import axios from "axios";

const props = defineProps({
  fileListExpand: Boolean,
  enableStreamOutput: Boolean,
  enableHistoryContext: {
    type: Boolean,
    default: true
  },
  noteType: {
    type: String,
    default: "general"
  },
  useImg2txt: {
    type: Boolean,
    default: false
  }
});
const emits = defineEmits([
  "update:fileListExpand", 
  "closeAll", 
  "update:enableStreamOutput", 
  "update:enableHistoryContext",
  "update:noteType",
  "update:useImg2txt"
]);
const fileListExpand = computed({
  get() {
    return props.fileListExpand;
  },
  set(val) {
    emits("update:fileListExpand", val);
  }
});

const enableStreamOutput = computed({
  get() {
    return props.enableStreamOutput;
  },
  set(val) {
    emits("update:enableStreamOutput", val);
  }
});

const enableHistoryContext = computed({
  get() {
    return props.enableHistoryContext;
  },
  set(val) {
    emits("update:enableHistoryContext", val);
  }
});

const noteType = computed({
  get() {
    return props.noteType;
  },
  set(val) {
    emits("update:noteType", val);
  }
});

const useImg2txt = computed({
  get() {
    return props.useImg2txt;
  },
  set(val) {
    emits("update:useImg2txt", val);
  }
});

const menuRef = ref()
const activeIndex = ref("home")
const openSettings = ref(false)
const expandedFileId = ref(null)
const fileEntities = ref({})
const loadingEntities = ref({})

const openMenuItem = (index) => {
  activeIndex.value = index;
}
const menuItemSelect = (index) => {
  activeIndex.value = index;
  if (index === "fileList") {
    fileListExpand.value = true;
  } else if (index === "home") {
    fileListExpand.value = false;
    emits("closeAll");
  }
}

const toggleFileExpand = async (file) => {
  if (!file || file.status !== 'completed') return;
  
  if (expandedFileId.value === file.name) {
    expandedFileId.value = null;
    return;
  }
  
  expandedFileId.value = file.name;
  
  if (!fileEntities.value[file.name] && !loadingEntities.value[file.name]) {
    try {
      loadingEntities.value[file.name] = true;
      const response = await axios.get(`http://localhost:8000/file-entities/${file.name}`);
      if (response.data && response.data.entities) {
        fileEntities.value[file.name] = {
          entities: response.data.entities,
          errorMessage: null
        };
      }
    } catch (error) {
      console.error('获取文件实体失败:', error);
      fileEntities.value[file.name] = {
        entities: [],
        errorMessage: error.response?.data?.error || '获取文件实体失败'
      };
    } finally {
      loadingEntities.value[file.name] = false;
    }
  }
}

// 笔记类型选项
const noteTypeOptions = [
  {
    value: 'general',
    label: '通用',
    color: '#409eff' // 蓝色，对应默认主题的主色调
  },
  {
    value: 'story',
    label: '故事',
    color: '#67c23a' // 绿色，使其与通用类型区分
  }
];

// 获取当前选中的笔记类型显示文本和颜色
const selectedNoteTypeLabel = computed(() => {
  const selected = noteTypeOptions.find(item => item.value === noteType.value);
  return selected ? selected.label : '';
});

const selectedNoteTypeColor = computed(() => {
  const selected = noteTypeOptions.find(item => item.value === noteType.value);
  return selected ? selected.color : '';
});

defineExpose({
  openMenuItem,
  expandedFileId,
  fileEntities,
  loadingEntities,
  toggleFileExpand
})
</script>

<template>
  <el-menu class="menu" ref="menuRef" :default-active="activeIndex" @select="menuItemSelect">
    <div class="logo">
      <svg-icon icon-name="logo" size="32px"/>
    </div>
    <el-menu-item index="home">
      <div class="menu-item">
        <svg-icon icon-name="home" size="22px"/>
      </div>
    </el-menu-item>
    <el-menu-item index="fileList">
      <div class="menu-item">
        <svg-icon icon-name="file" size="22px"/>
      </div>
    </el-menu-item>
    <div class="flex-grow"/>
    <el-menu-item @click="openSettings=true">
      <div class="menu-item">
        <svg-icon icon-name="setting" size="24px"/>
      </div>
    </el-menu-item>
  </el-menu>

  <el-dialog 
    v-model="openSettings" 
    width="520px" 
    :close-on-click-modal="false" 
    :show-close="false"
    style="border-radius: 8px"
    class="settings-dialog"
  >
    <template #header>
      <div class="settings-dialog-header">
        <div class="settings-title">设置</div>
        <svg-icon icon-name="close" icon-class="close-icon" size="18px" @click="openSettings=false"/>
      </div>
    </template>
    <template #default>
      <div class="settings-content">
        <div class="settings-section">
          <div class="section-title">图谱构建设置</div>
          <div class="settings-item">
            <span class="item-label">笔记类型</span>
            <el-select 
              v-model="noteType" 
              placeholder="请选择笔记类型" 
              style="width: 140px"
              popper-class="note-type-dropdown"
            >
              <template #prefix>
                <span class="note-type-dot" :style="{ backgroundColor: selectedNoteTypeColor }"></span>
              </template>
              
              <el-option
                v-for="item in noteTypeOptions"
                :key="item.value"
                :value="item.value"
                :label="item.label"
              >
                <div class="note-type-option-content">
                  <span class="note-type-color-indicator" :style="{ backgroundColor: item.color }"></span>
                  <span class="note-type-label">{{ item.label }}</span>
                </div>
              </el-option>
            </el-select>
          </div>
          <div class="item-description">
            选择不同的笔记类型，AI将根据类型构建相应的知识图谱结构。
          </div>
          
          <div class="settings-item">
            <span class="item-label">PDF图片内容识别</span>
            <el-switch 
              v-model="useImg2txt"
              active-text="开启"
              inactive-text="关闭"
            />
          </div>
          <div class="item-description">
            开启后，处理PDF文件时将使用QwenVL视觉模型对图片进行识别转为图片内容描述。
          </div>
        </div>
        
        <div class="settings-section">
          <div class="section-title">RAG问答设置</div>
          <div class="settings-item">
            <span class="item-label">启用流式输出</span>
            <el-switch 
              v-model="enableStreamOutput"
              active-text="开启"
              inactive-text="关闭"
            />
          </div>
          <div class="item-description">
            开启后，AI回答将实时流式输出，使对话更加自然流畅。
          </div>
          
          <div class="settings-item">
            <span class="item-label">携带历史上下文</span>
            <el-switch 
              v-model="enableHistoryContext"
              active-text="开启"
              inactive-text="关闭"
            />
          </div>
          <div class="item-description">
            开启后，AI回答会参考之前的对话历史，保持上下文连贯性。
          </div>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.menu {
  display: flex;
  flex-direction: column;
  width: 64px;
  position: inherit;
  background-color: inherit;
  border: none;
  padding-top: 16px;
  padding-bottom: 12px;

  .logo {
    margin-bottom: 8px;
    text-align: center;
  }

  .el-menu-item {
    display: flex;
    justify-content: center;
    position: inherit;
  }

  .el-menu-item:hover {
    background-color: inherit;
  }

  .el-menu-item.is-active {
    background-color: inherit;

    .menu-item {
      background-color: var(--el-fill-color-darker);
    }
  }

  .menu-item {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 8px;
    border-radius: 8px;
  }

  .menu-item:hover {
    background-color: var(--el-fill-color-darker);
  }

  .flex-grow {
    flex: 1;
  }
}

.settings-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 18px;
  font-weight: 600;
  line-height: 28px;

  .settings-title {
    color: var(--el-color-primary);
    font-size: 20px;
  }

  .close-icon {
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
  }

  .close-icon:hover {
    background-color: var(--el-fill-color-light);
  }
}

.settings-content {
  padding: 0 16px;

  .settings-section {
    margin-bottom: 24px;

    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--el-color-primary) !important;
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--el-border-color-light);
    }

    .settings-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;

      .item-label {
        font-size: 14px;
        color: var(--el-text-color-primary);
        font-weight: 500;
      }
    }

    .item-description {
      font-size: 12px;
      color: var(--el-text-color-regular) !important;
      line-height: 1.5;
      margin-top: 4px;
      padding-left: 4px;
      margin-bottom: 16px;
    }
  }

  :deep(.el-select) {
    .el-input__wrapper {
      background-color: var(--el-fill-color-darker) !important;
      box-shadow: 0 0 0 1px var(--el-border-color) inset !important;
    }
    
    .el-input__inner {
      color: var(--el-text-color-primary) !important;
      font-weight: 500 !important;
    }
  }
  
  :deep(.el-select-dropdown__item) {
    color: var(--el-text-color-primary);
  }
  
  :deep(.el-select-dropdown__item.selected) {
    color: var(--el-color-primary);
  }
  
  :deep(.el-select-dropdown) {
    background-color: var(--el-fill-color-darker);
    border: 1px solid var(--el-border-color);
    
    .el-select-dropdown__item {
      color: var(--el-text-color-primary);
      
      &:hover, &.hover {
        background-color: var(--el-fill-color-light);
      }
      
      &.selected {
        color: var(--el-color-primary);
        font-weight: bold;
      }
    }
    
    .note-type-option {
      color: #ffffff;
      font-weight: 500;
      
      &:hover {
        color: var(--el-color-primary-light-3);
      }
      
      &.selected {
        color: var(--el-color-primary);
      }
    }
  }
}

.note-type-option-content {
  display: flex;
  align-items: center;
  
  .note-type-color-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
    flex-shrink: 0;
    border: 1px solid rgba(255, 255, 255, 0.2);
  }
  
  .note-type-label {
    color: var(--el-text-color-primary);
    font-weight: 500;
  }
}

.note-type-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

:deep(.el-select .el-input__wrapper) {
  padding-left: 8px;
}

:deep(.el-select .el-input__inner) {
  padding-left: 4px;
  font-weight: 500;
  color: #ffffff;
}

:deep(.el-select .el-select__tags) {
  background-color: transparent;
}

/* 增强设置dialog和项目的对比度 */
:deep(.settings-dialog) {
  .el-dialog__header, .el-dialog__body {
    padding: 16px;
  }
}

:deep(.settings-section) {
  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-color-primary) !important;
  }
  
  .item-label {
    font-weight: 500;
  }
  
  .item-description {
    color: var(--el-text-color-regular) !important;
  }
}
</style>

<style lang="scss">
/* 全局样式，确保能够应用到弹出的下拉框 */
body[data-theme="dark"] {
  .el-popper.is-light {
    background-color: var(--el-select-dropdown-bg-color, #2a2a2a) !important;
    border-color: var(--el-border-color, #4c4d4f) !important;
  }
  
  .el-select-dropdown__item {
    color: #e5eaf3 !important; /* 使用更亮的颜色，提高未选中项的可读性 */
    font-weight: 500 !important;
    
    &:hover, &.hover {
      background-color: var(--el-select-dropdown-item-hover-bg, #3a3a3a) !important;
      color: #ffffff !important; /* 悬停时使用白色 */
    }
    
    &.selected {
      color: var(--el-select-dropdown-item-selected-color, #67c23a) !important;
      font-weight: bold !important;
      background-color: rgba(103, 194, 58, 0.15) !important;
    }
  }
  
  /* 特别针对笔记类型选项增加样式 */
  .note-type-option {
    color: #ffffff !important; /* 直接使用白色，最大对比度 */
    text-shadow: 0 0 1px rgba(255, 255, 255, 0.3); /* 添加轻微文字阴影增强可读性 */
  }
  
  .el-popper__arrow::before {
    background-color: var(--el-select-dropdown-bg-color, #2a2a2a) !important;
    border-color: var(--el-border-color, #4c4d4f) !important;
  }
  
  /* 自定义笔记类型选项样式 */
  .el-select-dropdown__item .note-type-option-content {
    .note-type-label {
      color: #ffffff !important;
      font-weight: 500;
    }
  }
  
  .el-select-dropdown__item.selected .note-type-option-content {
    .note-type-label {
      color: var(--el-color-primary) !important;
      font-weight: bold;
    }
  }

  /* 自定义下拉菜单背景 */
  .note-type-dropdown {
    background-color: #2a2a2a !important;
    border: 1px solid #4c4d4f !important;
    
    .el-select-dropdown__item {
      height: auto;
      padding: 8px 12px;
      
      &:hover, &.hover {
        background-color: #3a3a3a !important;
      }
      
      &.selected {
        background-color: #424242 !important;
      }
      
      .note-type-option-content {
        .note-type-label {
          color: #ffffff !important;
          font-weight: 500;
          text-shadow: 0 0 1px rgba(0, 0, 0, 0.5);
        }
      }
    }
  }
  
  /* 选择器内部样式 */
  .el-select .el-input__wrapper {
    background-color: rgba(54, 54, 55, 0.8) !important;
    box-shadow: 0 0 0 1px #4c4d4f inset !important;
  }
  
  .el-select .el-input__inner {
    color: #ffffff !important;
  }
  
  /* Popper箭头样式 */
  .el-popper.note-type-dropdown .el-popper__arrow::before {
    background-color: #2a2a2a !important;
    border-color: #4c4d4f !important;
  }

  /* 设置对话框样式优化 */
  .settings-dialog {
    .el-dialog {
      background-color: #2c2c2c !important; /* 更亮一点的背景色 */
      border: 1px solid #4c4d4f !important;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }
  }

  /* 选项标签样式 */
  .settings-content {
    .settings-section {
      .section-title {
        color: #409eff !important;
        border-bottom-color: #4c4d4f !important;
      }
      
      .settings-item {
        .item-label {
          color: #d16161;
          font-weight: 600;
          text-shadow: 0 0 1px rgba(255, 255, 255, 0.2);
        }
      }
      
      .item-description {
        color: #b8b8b8 !important;
      }
    }
  }
  
  /* 增强选择器样式 */
  .el-select-dropdown__item {
    color: #e6e6e6 !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    
    &:hover, &.hover {
      background-color: #3a3a3a !important;
    }
    
    &.selected {
      background-color: rgba(64, 158, 255, 0.2) !important;
      color: #67c23a !important;
      font-weight: bold !important;
    }
  }
  
  /* 开关组件增强 */
  .el-switch__label {
    color: #e6e6e6 !important;
    
    &.is-active {
      color: #67c23a !important;
    }
  }
}
</style>