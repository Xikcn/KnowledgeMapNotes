<script setup>
import {computed, ref} from 'vue'
import SvgIcon from "@/components/SvgIcon/index.vue";

const props = defineProps({
  fileListExpand: Boolean,
  enableStreamOutput: Boolean,
});
const emits = defineEmits(["update:fileListExpand", "closeAll", "update:enableStreamOutput"]);
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

const menuRef = ref()
const activeIndex = ref("home")
const openSettings = ref(false)

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
defineExpose({
  openMenuItem
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
    }
  }
}
</style>