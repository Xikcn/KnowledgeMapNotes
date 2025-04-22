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
  }
});
const emits = defineEmits([
  "update:fileListExpand", 
  "closeAll", 
  "update:enableStreamOutput", 
  "update:enableHistoryContext",
  "update:noteType"
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

  <el-dialog v-model="openSettings" width="520px" :close-on-click-modal="false" :show-close="false"
             style="border-radius: 8px">
    <template #header>
      <div class="settings-dialog-header">
        <div>设置</div>
        <svg-icon icon-name="close" icon-class="close-icon" size="18px" @click="openSettings=false"/>
      </div>
    </template>
    <template #default>
      <div class="settings-content">
        <div class="settings-section">
          <div class="section-title">图谱构建设置</div>
          <div class="settings-item">
            <span class="item-label">笔记类型</span>
            <el-select v-model="noteType" placeholder="请选择笔记类型" style="width: 140px">
              <el-option
                label="通用"
                value="general"
              />
              <el-option
                label="故事"
                value="story"
              />
            </el-select>
          </div>
          <div class="item-description">
            选择不同的笔记类型，AI将根据类型构建相应的知识图谱结构。
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
            开启后，AI回答将实时流式显示，使对话更加自然流畅。
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

<style scoped>
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
      color: var(--el-text-color-primary);
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
      }
    }

    .item-description {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      line-height: 1.5;
      margin-top: 4px;
      padding-left: 4px;
      margin-bottom: 16px;
    }
  }
}
</style>