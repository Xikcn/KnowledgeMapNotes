<script setup>
import SideBar from "./components/SideBar.vue";
import {ref, reactive, onMounted, watch} from "vue";
import SvgIcon from "@/components/SvgIcon/index.vue";
import {Link, Document, Loading, SuccessFilled, Download, ChatDotRound, Tickets, View, Hide} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';
import { themes, applyTheme } from '@/styles/theme';

const sideBarRef = ref();
const fileListExpand = ref(false);
const isSearch = ref(false);
const searchValue = ref('');
const uploadFileList = ref([]);
const filteredFileList = ref([]);
const currentHtml = ref('');
const showHtmlContent = ref(false);
const htmlIframe = ref(null);

// 新增顶部导航和视图控制
const activeView = ref('upload'); // 'upload', 'result'
const activeTab = ref('original'); // 'original', 'knowledge-graph', 'rag'
const currentFile = ref(null); // 当前选中的文件

// 面板显示状态
const panelVisible = reactive({
  original: true,
  'knowledge-graph': true,
  rag: true
});

// RAG聊天相关
const chatMessages = ref([
  { role: 'system', content: '我是基于当前文档的HybridRAG助手，可以回答与文档相关的问题。' }
]);
const userInput = ref('');
const chatLoading = ref(false);

// 添加文件内容相关状态
const fileContent = ref('');
const fileContentLoading = ref(false);

// 在 script setup 部分添加
const knowledgeGraphData = ref(null);
const knowledgeGraphLoading = ref(false);

// 修改主题相关状态
const themeOptions = [
  { name: '默认主题', value: 'default' },
  { name: '暗色主题', value: 'dark' },
  { name: '蓝色主题', value: 'blue' },
  { name: '护眼主题', value: 'green' }
];
const currentTheme = ref('default');

// 修改主题切换函数
const changeTheme = (theme) => {
  currentTheme.value = theme;
  applyTheme(theme);
  localStorage.setItem('app-theme', theme);
};

// 获取知识图谱数据
const fetchKnowledgeGraph = async (filename) => {
  if (!filename) {
    console.error('文件名不能为空');
    return;
  }

  try {
    knowledgeGraphLoading.value = true;

    // 检查本地缓存
    const cachedData = localStorage.getItem(`kg_${filename}`);
    if (cachedData) {
      knowledgeGraphData.value = JSON.parse(cachedData);
      return;
    }

    // 从服务器获取数据
    const response = await axios.get(`http://localhost:8000/result/${filename}`);
    if (response.data) {
      knowledgeGraphData.value = response.data;
      // 缓存数据
      localStorage.setItem(`kg_${filename}`, JSON.stringify(response.data));
    }
  } catch (error) {
    console.error('获取知识图谱失败:', error);
    ElMessage.error('获取知识图谱失败');
  } finally {
    knowledgeGraphLoading.value = false;
  }
};

// 页面加载时获取历史文件列表
onMounted(async () => {
  try {
    // 初始化主题
    const savedTheme = localStorage.getItem('app-theme') || 'default';
    changeTheme(savedTheme);

    const response = await axios.get('http://localhost:8000/list-files');
    if (response.data && Array.isArray(response.data.files)) {
      // 将历史文件添加到文件列表，保持原始文件名
      uploadFileList.value = response.data.files.map(file => ({
        name: file.filename || file.name || file,  // 保持原始文件名
        status: file.status || 'completed',
        size: file.size || 0,
        percentage: 100
      }));

      // 初始化过滤后的文件列表
      filteredFileList.value = [...uploadFileList.value];

      // 检查是否有未完成的文件
      uploadFileList.value.forEach(file => {
        if (file.status === 'processing' || file.status === 'uploading') {
          checkFileProcessingStatus(file);
        }
      });
    }
  } catch (error) {
    console.error('获取历史文件列表失败:', error);
    ElMessage.error('获取历史文件列表失败');
  }
});

// 删除文件
const deleteFile = async (file) => {
  try {
    // 添加确认弹窗
    await ElMessageBox.confirm(
      `确定要删除文件 ${file.name} 吗？此操作将同时删除相关的聊天记录和知识图谱。`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    await axios.delete(`http://localhost:8000/delete/${file.name}`);

    // 从列表中移除文件
    const index = uploadFileList.value.findIndex(item => item.name === file.name);
    if (index !== -1) {
      uploadFileList.value.splice(index, 1);
    }

    // 清理本地缓存
    localStorage.removeItem(`kg_${file.name}`);  // 删除知识图谱数据
    localStorage.removeItem(`chat_${file.name}`);  // 删除聊天记录

    // 如果删除的是当前查看的文件，关闭结果视图
    if (currentFile.value && currentFile.value.name === file.name) {
      closeResultView();
    }

    ElMessage.success(`文件 ${file.name} 已删除`);
  } catch (error) {
    if (error !== 'cancel') {  // 如果不是用户取消操作
      console.error('删除文件失败:', error);
      ElMessage.error('删除文件失败');
    }
  }
};

// 修改RAG请求函数
const sendMessage = async () => {
  if (!userInput.value.trim() || chatLoading.value) return;

  // 首先检查是否有选中的文件
  if (!currentFile.value?.name) {
    ElMessage.error('请先选择一个文件');
    return;
  }

  chatMessages.value.push({ role: 'user', content: userInput.value });
  const currentQuestion = userInput.value;
  userInput.value = '';
  chatLoading.value = true;

  chatMessages.value.push({ role: 'assistant', content: '思考中...', thinking: true });

  try {
    // 处理历史消息，确保格式正确
    const historyMessages = chatMessages.value
      .filter(msg => !msg.thinking && msg.role !== 'system')
      .map(msg => {
        if (msg.role === 'assistant' && typeof msg.content === 'object') {
          return {
            role: msg.role,
            content: Array.isArray(msg.content.answer)
              ? msg.content.answer.join('\n')
              : msg.content.answer
          };
        }
        return {
          role: msg.role,
          content: msg.content
        };
      });

    const response = await axios.post('http://localhost:8000/hybridrag', {
      request: currentQuestion,
      model: 'deepseek',
      flow: false,
      filename: currentFile.value.name,
      messages: historyMessages
    });

    // 检查响应是否有效
    if (!response || !response.data) {
      throw new Error('服务器响应无效');
    }

    // 检查响应状态
    if (response.data.status === 'processing') {
      ElMessage.warning('文件正在处理中，请稍后再试');
      chatMessages.value = chatMessages.value.filter(msg => !msg.thinking);
      return;
    } else if (response.data.status === 'error') {
      ElMessage.error(response.data.message || '文件处理失败');
      chatMessages.value = chatMessages.value.filter(msg => !msg.thinking);
      return;
    }

    // 检查结果是否存在
    if (!response.data.result) {
      throw new Error('服务器返回结果为空');
    }

    const thinkingIndex = chatMessages.value.findIndex(msg => msg.thinking);
    if (thinkingIndex !== -1) {
      chatMessages.value[thinkingIndex] = {
        role: 'assistant',
        content: {
          answer: response.data.result.answer,
          material: response.data.result.material
        }
      };
    }

    // 保存聊天记录到localStorage
    if (currentFile.value?.name) {
      const chatHistory = chatMessages.value.filter(msg => !msg.thinking);
      localStorage.setItem(`chat_${currentFile.value.name}`, JSON.stringify(chatHistory));
    }
  } catch (error) {
    console.error('获取RAG回复失败:', error);
    chatMessages.value = chatMessages.value.filter(msg => !msg.thinking);
    if (error.response) {
      if (error.response.status === 422) {
        ElMessage.error('请求参数错误：' + (error.response.data.detail?.[0]?.msg || '未知错误'));
      } else {
        ElMessage.error(`服务器错误: ${error.response.status} - ${error.response.data?.message || '未知错误'}`);
      }
    } else if (error.message) {
      ElMessage.error(error.message);
    } else {
      ElMessage.error('获取回复失败，请稍后重试');
    }
  } finally {
    chatLoading.value = false;
  }
};

const menuItemSelect = (index) => {
  if (index === "home") {
    fileListExpand.value = false;
    activeView.value = 'upload';  // 切换到上传视图
    currentFile.value = null;     // 清空当前文件
  } else if (index === "fileList") {
    fileListExpand.value = true;
  }
}

// 修改 closeFileList 函数
const closeFileList = () => {
  sideBarRef.value.openMenuItem("home");
  fileListExpand.value = false;
}

// 文件状态: 'uploading', 'processing', 'success', 'error'
const beforeUpload = (file) => {
  const fileObj = {
    uid: Date.now(),
    name: file.name,  // 保持原始文件名（包含后缀）
    status: 'uploading',
    size: file.size,
    percentage: 0
  }
  uploadFileList.value.push(fileObj);
  fileListExpand.value = true;
  return true;
}

const onUploadProgress = (event, file) => {
  const targetFile = uploadFileList.value.find(item => item.name === file.name);
  if (targetFile) {
    targetFile.percentage = Math.round(event.percent);
  }
}

const onUploadSuccess = (response, file) => {
  const targetFile = uploadFileList.value.find(item => item.name === file.name);
  if (targetFile) {
    // 修改状态为处理中，不再立即设置为成功
    targetFile.status = 'processing';
    targetFile.percentage = 100;
    targetFile.resultId = response.resultId || Date.now();

    // 开始检查处理状态
    checkFileProcessingStatus(targetFile);
  }
}

// 添加检查文件处理状态的函数
const checkFileProcessingStatus = (file) => {
  if (!file) return;

  // 创建定时器，每3秒检查一次处理状态
  const checkStatus = async () => {
    try {
      // 修改为正确的API路径
      const response = await axios.get(`http://localhost:8000/processing-status/${file.name}`);

      if (response.data && response.data.status) {
        const status = response.data.status;

        if (status === 'completed') {
          // 处理完成
          file.status = 'completed';  // 使用 completed 而不是 success
          ElMessage.success(`文件 ${file.name} 处理完成`);
          return; // 停止检查
        } else if (status.startsWith('error')) {
          // 处理出错
          file.status = 'error';
          ElMessage.error(`文件 ${file.name} 处理失败: ${status.replace('error: ', '')}`);
          return; // 停止检查
        }
        // 如果仍在处理中，继续轮询
        setTimeout(checkStatus, 3000);
      } else {
        // 状态未知，继续轮询
        setTimeout(checkStatus, 3000);
      }
    } catch (error) {
      console.error('检查处理状态失败:', error);
      // 发生错误时，继续轮询，但增加间隔时间
      setTimeout(checkStatus, 5000);
    }
  };

  // 开始检查
  setTimeout(checkStatus, 2000);
};

const onUploadError = (error, file) => {
  const targetFile = uploadFileList.value.find(item => item.name === file.name);
  if (targetFile) {
    targetFile.status = 'error';
    ElMessage.error(`文件 ${file.name} 上传失败`);
  }
}

// 查看文件结果
const viewFileResult = async (file) => {
  if (file.status === 'completed') {
    try {
      activeView.value = 'result';
      currentFile.value = file;

      fileContentLoading.value = true;
      fileContent.value = '';

      if (!file.name) {
        ElMessage.error('文件名不存在');
        return;
      }

      try {
        const [contentResponse] = await Promise.all([
          // 使用原始文件名获取内容
          axios.get(`http://localhost:8000/file-content/${file.name}`).catch(error => {
            console.error('获取文件内容失败:', error);
            return { data: { content: '' } };
          }),
          fetchKnowledgeGraph(file.name)  // 使用原始文件名获取知识图谱
        ]);

        if (contentResponse.data && contentResponse.data.content) {
          fileContent.value = contentResponse.data.content;
        }
      } catch (error) {
        console.error('获取文件内容失败:', error);
        ElMessage.warning('获取原文件内容失败');
      } finally {
        fileContentLoading.value = false;
      }

      // 加载聊天记录时使用原始文件名
      const savedChat = localStorage.getItem(`chat_${file.name}`);
      if (savedChat) {
        chatMessages.value = JSON.parse(savedChat);
      } else {
        chatMessages.value = [
          { role: 'system', content: '我是基于当前文档的HybridRAG助手，可以回答与文档相关的问题。' }
        ];
      }
    } catch (error) {
      ElMessage.error('获取结果失败');
      console.error('获取结果失败:', error);
    }
  }
}

// 关闭结果视图
const closeResultView = () => {
  if (currentFile.value?.name) {
    const chatHistory = chatMessages.value.filter(msg => !msg.thinking);
    localStorage.setItem(`chat_${currentFile.value.name}`, JSON.stringify(chatHistory));
  }
  activeView.value = 'upload';
  knowledgeGraphData.value = null;
  chatMessages.value = [
    { role: 'system', content: '我是基于当前文档的HybridRAG助手，可以回答与文档相关的问题。' }
  ];
}

// 修改切换面板显示状态的函数
const togglePanelVisibility = (panel) => {
  // 记录之前的状态
  const previousState = panelVisible[panel];

  // 避免关闭所有面板
  const visibleCount = Object.values(panelVisible).filter(v => v).length;
  if (visibleCount > 1 || !panelVisible[panel]) {
    panelVisible[panel] = !panelVisible[panel];

    // 如果当前激活的面板被关闭，则切换到第一个可见面板
    if (activeTab.value === panel && !panelVisible[panel]) {
      const firstVisiblePanel = Object.keys(panelVisible).find(key => panelVisible[key]);
      if (firstVisiblePanel) {
        activeTab.value = firstVisiblePanel;
      }
    }

    // 如果知识图谱面板从隐藏变为显示，则重新加载
    if (panel === 'knowledge-graph' && !previousState && panelVisible[panel]) {
      reloadKnowledgeGraph();
    }
  } else {
    ElMessage.warning('至少保留一个面板');
  }
};

// 切换标签
const switchTab = (tab) => {
  if (panelVisible[tab]) {
    activeTab.value = tab;
  }
};

const getStatusText = (status) => {
  switch(status) {
    case 'uploading': return '上传中';
    case 'processing': return '处理中';
    case 'completed': return '已完成';
    case 'error': return '失败';
    default: return '未知';
  }
}

const getFileIcon = (status) => {
  switch(status) {
    case 'uploading': return Loading;
    case 'processing': return Loading;
    case 'completed': return SuccessFilled;
    case 'error': return Document;
    default: return Document;
  }
}

// 修改重新加载知识图谱函数
const reloadKnowledgeGraph = () => {
  if (panelVisible['knowledge-graph'] && currentFile.value?.name) {
    fetchKnowledgeGraph(currentFile.value.name);
  }
};

// 添加筛选相关的状态
const fileTypeFilter = ref('all');
const statusFilter = ref('all');

// 文件类型选项
const fileTypeOptions = [
  { value: 'all', label: '全部' },
  { value: 'txt', label: 'TXT' },
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'WORD' }
];

// 状态选项
const statusOptions = [
  { value: 'all', label: '全部' },
  { value: 'uploading', label: '上传中' },
  { value: 'processing', label: '处理中' },
  { value: 'completed', label: '已完成' },
  { value: 'error', label: '失败' }
];

// 添加临时筛选状态
const tempFileTypeFilter = ref('all');
const tempStatusFilter = ref('all');

// 添加筛选框显示控制
const filterVisible = ref(false);

// 修改筛选处理函数
const handleFilter = () => {
  let filtered = uploadFileList.value;

  // 应用搜索过滤
  if (searchValue.value) {
    const searchText = searchValue.value.toLowerCase();
    filtered = filtered.filter(file =>
      file.name.toLowerCase().includes(searchText)
    );
  }

  // 应用类型过滤
  if (fileTypeFilter.value !== 'all') {
    filtered = filtered.filter(file => {
      const ext = file.name.split('.').pop().toLowerCase();
      return ext === fileTypeFilter.value;
    });
  }

  // 应用状态过滤
  if (statusFilter.value !== 'all') {
    filtered = filtered.filter(file =>
      file.status === statusFilter.value
    );
  }

  filteredFileList.value = filtered;
};

// 修改确认筛选函数
const confirmFilter = () => {
  fileTypeFilter.value = tempFileTypeFilter.value;
  statusFilter.value = tempStatusFilter.value;
  handleFilter();
  filterVisible.value = false;  // 关闭筛选框
};

// 修改重置筛选函数
const resetFilter = () => {
  tempFileTypeFilter.value = 'all';
  tempStatusFilter.value = 'all';
  fileTypeFilter.value = 'all';
  statusFilter.value = 'all';
  handleFilter();
  filterVisible.value = false;  // 关闭筛选框
};

// 监听筛选条件变化
watch([searchValue, fileTypeFilter, statusFilter], () => {
  handleFilter();
}, { deep: true });

// 监听文件列表变化
watch(uploadFileList, () => {
  handleFilter();
}, { deep: true });

// 添加关闭所有视图的处理函数
const handleCloseAll = () => {
  closeResultView();
  fileListExpand.value = false;
};

// 添加当前选中文件的ID
const currentFileId = ref(null);
</script>

<template>
  <div class="main-container">
    <side-bar
      ref="sideBarRef"
      v-model:fileListExpand="fileListExpand"
      @closeAll="handleCloseAll"
    />
    <div class="main-content">
      <el-drawer v-model="fileListExpand" direction="ltr" :modal="false" :show-close="false" :size="280">
        <template #header>
          <div class="drawer-manu-header">
            <div class="header">
              <svg-icon icon-name="file" size="18px"/>
              <span>文件列表</span>
            </div>
            <svg-icon icon-name="close" icon-class="close-icon" size="18px" @click="closeFileList"/>
          </div>
        </template>
        <template #default>
          <div v-if="!isSearch" class="query-button">
            <el-popover
              v-model:visible="filterVisible"
              :show-arrow="false"
              placement="top-end"
              popper-class="custom-popover"
              trigger="click"
              :show-after="200"
              popper-style="width:360px"
            >
              <template #reference>
                <div class="filter">
                  <svg-icon icon-name="filter" size="16px"/>
                  <span>筛选</span>
                </div>
              </template>
              <template #default>
                <div class="filter-content">
                  <div class="filter-section">
                    <div class="filter-title">类型</div>
                    <div class="filter-options">
                      <el-radio-group v-model="tempFileTypeFilter" size="small">
                        <template v-for="option in fileTypeOptions" :key="option.value">
                          <el-radio-button :value="option.value">{{ option.label }}</el-radio-button>
                        </template>
                      </el-radio-group>
                    </div>
                  </div>
                  <div class="filter-section">
                    <div class="filter-title">状态</div>
                    <div class="filter-options">
                      <el-radio-group v-model="tempStatusFilter" size="small">
                        <template v-for="option in statusOptions" :key="option.value">
                          <el-radio-button :value="option.value">{{ option.label }}</el-radio-button>
                        </template>
                      </el-radio-group>
                    </div>
                  </div>
                  <div class="filter-actions">
                    <el-button size="small" @click="resetFilter">重置</el-button>
                    <el-button type="primary" size="small" @click="confirmFilter">确认</el-button>
                  </div>
                </div>
              </template>
            </el-popover>
            <svg-icon icon-name="search" icon-class="search-icon" size="18px" @click="isSearch=true"/>
          </div>
          <div v-else class="search-input">
            <el-input
              v-model="searchValue"
              placeholder="请输入文件名称"
              clearable
              @input="handleSearch"
            />
            <el-button link @click="isSearch=false">取消</el-button>
          </div>
          <div class="file-list">
            <template v-if="filteredFileList.length > 0">
              <div
                v-for="file in filteredFileList"
                :key="file.name"
                class="file-item"
                :class="{
                  'can-click': file.status === 'completed',
                  'active': currentFile?.name === file.name
                }"
                @dblclick="viewFileResult(file)"
                @mouseenter="currentFileId = file.name"
                @mouseleave="currentFileId = null"
              >
                <div class="file-info">
                  <el-icon class="file-icon" :class="file.status">
                    <component :is="getFileIcon(file.status)" />
                  </el-icon>
                  <div class="file-name-container">
                    <el-tooltip
                      :content="file.name"
                      placement="right"
                      :show-after="500"
                      :hide-after="0"
                    >
                      <div class="file-name">{{ file.name }}</div>
                    </el-tooltip>
                    <div v-if="file.status === 'uploading'" class="file-progress">
                      <el-progress :percentage="file.percentage" :show-text="false" :stroke-width="2" />
                    </div>
                  </div>
                </div>
                <div class="file-actions">
                  <div class="file-status" :class="file.status">
                    {{ getStatusText(file.status) }}
                  </div>
                  <transition name="fade">
                    <div v-if="currentFileId === file.name && file.status === 'completed'" class="delete-action">
                      <img
                        src="@/assets/icons/svg/delete.svg"
                        alt="删除"
                        class="delete-icon"
                        @click.stop="deleteFile(file)"
                      />
                    </div>
                  </transition>
                </div>
              </div>
            </template>
            <el-empty v-else description="暂无文件" />
          </div>
          <div class="pagination" v-if="filteredFileList.length > 0">
            <el-pagination :total="filteredFileList.length" size="small" layout="prev, pager, next" background />
          </div>
        </template>
      </el-drawer>
      <div class="content" :style="{marginLeft:fileListExpand?'280px':'auto'}">
        <div v-if="activeView === 'upload'" class="upload-view">
          <div class="background"></div>
          <div class="upload">
            <h1>知识图谱构建系统! 🎉</h1>
            <el-upload
                drag
                action="/api/upload"
                multiple
                :show-file-list="false"
                :before-upload="beforeUpload"
                :on-progress="onUploadProgress"
                :on-success="onUploadSuccess"
                :on-error="onUploadError"
            >
              <svg-icon icon-name="upload" icon-class="upload-icon" size="40px"/>
              <div class="upload-text">
                点击或拖拽上传文件
              </div>
              <p>单个文件不超过 xxxM 或 xxx 页</p>
              <p>单个图片不超过 xxM</p>
              <p>单个上传最多 xx 个文件</p>
              <el-button :icon="Link" size="large"> URL 上传</el-button>
            </el-upload>
          </div>
        </div>

        <div v-if="activeView === 'result'" class="result-view">
          <!-- 顶部导航标签 -->
          <div class="file-tabs">
            <div class="file-info">
              <span v-if="currentFile" class="filename">{{ currentFile.name }}</span>
            </div>
            <div class="tabs-container">
              <div
                  class="tab-item"
                  :class="{ active: activeTab === 'original', disabled: !panelVisible['original'] }"
                  @click="switchTab('original')"
              >
                <el-icon><Document /></el-icon>
                <span>原文件</span>
                <div class="tab-actions">
                  <div
                      class="panel-toggle"
                      :class="{ 'is-active': panelVisible['original'] }"
                      @click.stop="togglePanelVisibility('original')"
                  >
                    <el-icon><span>{{ panelVisible['original'] ? '✓' : '✕' }}</span></el-icon>
                  </div>
                </div>
              </div>
              <div
                  class="tab-item"
                  :class="{ active: activeTab === 'knowledge-graph', disabled: !panelVisible['knowledge-graph'] }"
                  @click="switchTab('knowledge-graph')"
              >
                <el-icon><Document /></el-icon>
                <span>知识图谱</span>
                <div class="tab-actions">
                  <div
                      class="panel-toggle"
                      :class="{ 'is-active': panelVisible['knowledge-graph'] }"
                      @click.stop="togglePanelVisibility('knowledge-graph')"
                  >
                    <el-icon><span>{{ panelVisible['knowledge-graph'] ? '✓' : '✕' }}</span></el-icon>
                  </div>
                </div>
              </div>
              <div
                  class="tab-item"
                  :class="{ active: activeTab === 'rag', disabled: !panelVisible['rag'] }"
                  @click="switchTab('rag')"
              >
                <el-icon><ChatDotRound /></el-icon>
                <span>RAG 问答</span>
                <div class="tab-actions">
                  <div
                      class="panel-toggle"
                      :class="{ 'is-active': panelVisible['rag'] }"
                      @click.stop="togglePanelVisibility('rag')"
                  >
                    <el-icon><span>{{ panelVisible['rag'] ? '✓' : '✕' }}</span></el-icon>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 内容区域 -->
          <div class="content-panels">
            <div
                v-if="panelVisible['original']"
                class="panel original-panel"
                :class="{ active: activeTab === 'original' }"
            >
              <div class="panel-header">
                <h3>原文件内容</h3>
                <el-button :icon="Download" circle size="small"></el-button>
              </div>
              <div class="panel-content">
                <div class="original-content">
                  <div v-if="fileContentLoading" class="loading-content">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>加载文件内容中...</span>
                  </div>
                  <div v-else-if="fileContent" class="document-content">
                    <pre class="file-text-content">{{ fileContent }}</pre>
                  </div>
                  <div v-else class="empty-content">
                    <el-empty description="无法加载文件内容" />
                  </div>
                </div>
              </div>
            </div>

            <div
                v-if="panelVisible['knowledge-graph']"
                class="panel knowledge-graph-panel"
                :class="{ active: activeTab === 'knowledge-graph' }"
            >
              <div class="panel-header">
                <h3>知识图谱</h3>
              </div>
              <div class="panel-content" style="overflow: hidden;">
                <div v-if="knowledgeGraphLoading" class="loading-content">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>加载知识图谱中...</span>
                </div>
                <div v-else-if="knowledgeGraphData" class="knowledge-graph-content">
                  <iframe
                    :srcdoc="knowledgeGraphData"
                    class="result-iframe"
                    frameborder="0"
                  ></iframe>
                </div>
                <div v-else class="empty-content">
                  <el-empty description="暂无知识图谱数据" />
                </div>
              </div>
            </div>

            <div
                v-if="panelVisible['rag']"
                class="panel rag-panel"
                :class="{ active: activeTab === 'rag' }"
            >
              <div class="panel-header">
                <h3>RAG 问答</h3>
              </div>
              <div class="panel-content">
                <div class="chat-container">
                  <div class="chat-messages">
                    <div v-for="(message, index) in chatMessages" :key="index"
                         :class="['message', message.role, {'thinking': message.thinking}]">
                      <div v-if="message.role === 'user'" class="avatar user-avatar">
                        <span>U</span>
                      </div>
                      <div v-else-if="message.role === 'assistant'" class="avatar assistant-avatar">
                        <span>AI</span>
                      </div>
                      <div class="message-content" :class="{'thinking': message.thinking}">
                        <div v-if="message.thinking" class="thinking-indicator">
                          <span></span><span></span><span></span>
                        </div>
                        <div v-else>
                          <template v-if="typeof message.content === 'object'">
                            <div class="answer">{{ Array.isArray(message.content.answer) ? message.content.answer.join('') : message.content.answer }}</div>
                            <div v-if="message.content.material && message.content.material.length > 0" class="material">
                              <div class="material-title">参考资料：</div>
                              <div class="material-content">{{ message.content.material }}</div>
                            </div>
                          </template>
                          <template v-else>
                            {{ message.content }}
                          </template>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="chat-input">
                    <el-input
                        v-model="userInput"
                        type="textarea"
                        :rows="2"
                        placeholder="输入问题..."
                        :disabled="chatLoading"
                        @keyup.enter.ctrl="sendMessage"
                    />
                    <el-button type="primary" :disabled="chatLoading" @click="sendMessage">
                      发送
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <el-popover :show-arrow="false" placement="top-end" popper-class="custom-popover" trigger="hover"
                    :show-after="200" popper-style="width:310px">
          <template #reference>
            <svg-icon icon-name="history" icon-class="history-icon" size="20px"/>
          </template>
          <template #default>
            <div class="theme-header">主题设置</div>
            <div class="theme-content">
              <div
                v-for="theme in themeOptions"
                :key="theme.value"
                class="theme-item"
                :class="{ active: currentTheme === theme.value }"
                @click="changeTheme(theme.value)"
              >
                <div class="theme-preview" :class="theme.value"></div>
                <span>{{ theme.name }}</span>
              </div>
            </div>
          </template>
        </el-popover>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.main-container {
  display: flex;
  box-sizing: border-box;
  height: 100vh;
  padding: 0 12px 8px 0;
  background-color: var(--el-fill-color-lighter);

  .main-content {
    position: relative;
    height: 100%;
    width: 100%;
    background-color: var(--el-bg-color);
    border-radius: 10px;
    box-shadow: 0 0 #0000, 0 0 #0000, 0 1px 2px 0 rgb(0 0 0 / .05);

    :deep(.el-drawer) {
      box-shadow: none;
      border-right: 1px solid var(--el-border-color-lighter);

      .el-drawer__header {
        padding: 12px 16px;
        margin: 0;
        border-bottom: 1px solid var(--el-border-color-lighter);

        .drawer-manu-header {
          color: var(--el-text-color-primary);
          display: flex;
          align-items: center;
          justify-content: space-between;

          .header {
            line-height: 30px;
            display: flex;
            align-items: center;
            font-weight: 600;

            span {
              margin-left: 4px;
            }
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
      }

      .el-drawer__body {
        display: flex;
        flex-direction: column;
        padding: 0;

        .query-button {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin: 12px 16px;

          .filter {
            line-height: 1.5;
            width: 80px;
            box-sizing: border-box;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: var(--el-fill-color-light);
            margin-right: 8px;
            padding: 4px 12px;
            border-radius: 6px;
            color: var(--el-text-color-primary);
            user-select: none;

            &:hover {
              background-color: var(--el-fill-color-dark);
            }
          }

          .search-icon {
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            color: var(--el-text-color-primary);

            &:hover {
              background-color: var(--el-fill-color-light);
            }
          }
        }

        .search-input {
          display: flex;
          margin: 12px 16px;

          .el-input__wrapper {
            box-sizing: border-box;
            box-shadow: none;
            border-radius: 100px;
            padding: 8px 8px 8px 20px;
            height: 32px;
            margin-right: 16px;
            background-color: var(--el-fill-color-light);
          }

          .el-button {
            color: var(--el-color-primary);
            font-size: 16px;
          }

          .el-button:hover {
            color: var(--el-color-danger);
          }
        }

        .file-list {
          flex: 1;
          padding: 0 16px;
          overflow-y: auto;

          .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            background-color: var(--el-fill-color-lighter);
            transition: all 0.3s ease;
            user-select: none;
            border: 1px solid transparent;

            &.active {
              background-color: var(--el-bg-color) !important;
              border-color: var(--el-border-color-light);
            }

            &:hover {
              background-color: var(--el-fill-color-dark);
            }

            &.can-click {
              cursor: pointer;

              &:hover {
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
              }

              &.active {
                background-color: var(--el-bg-color) !important;
                border-color: var(--el-color-primary-light-3);
              }
            }

            .file-actions {
              display: flex;
              align-items: center;
              gap: 12px;

              .delete-action {
                .delete-icon {
                  cursor: pointer;
                  width: 16px;
                  height: 16px;
                  padding: 4px;
                  border-radius: 4px;
                  transition: all 0.3s ease;
                  opacity: 0.6;

                  &:hover {
                    opacity: 1;
                    background-color: var(--el-color-danger-light-9);
                  }
                }
              }
            }

            .file-info {
              display: flex;
              align-items: center;
              flex: 1;
              min-width: 0; // 防止子元素溢出

              .file-icon {
                margin-right: 12px;
                font-size: 20px;
                flex-shrink: 0;

                &.uploading, &.processing {
                  color: var(--el-color-primary);
                  animation: spin 1.5s infinite linear;
                }

                &.completed {
                  color: var(--el-color-success);
                }

                &.error {
                  color: var(--el-color-danger);
                }
              }

              .file-name-container {
                flex: 1;
                min-width: 0; // 防止子元素溢出

                .file-name {
                  white-space: nowrap;
                  overflow: hidden;
                  text-overflow: ellipsis;
                  margin-bottom: 4px;
                  color: var(--el-text-color-primary);
                  font-weight: 500;
                  max-width: 100%;
                }

                .file-progress {
                  width: 100%;
                }
              }
            }

            .file-status {
              font-size: 12px;
              white-space: nowrap;
              flex-shrink: 0;

              &.uploading, &.processing {
                color: var(--el-color-primary);
              }

              &.completed {
                color: var(--el-color-success);
              }

              &.error {
                color: var(--el-color-danger);
              }
            }
          }
        }

        .pagination {
          margin: 16px auto;

          .el-pagination.is-background {
            .btn-prev, .btn-next, .el-pager li {
              font-size: 14px;
              margin: 0 2px;
              padding: 0 6px;
              border-radius: 6px;
              background-color: transparent;
            }

            .btn-prev:hover, .btn-next:hover, .el-pager li:hover {
              background-color: var(--el-fill-color-dark);
            }

            .btn-prev[disabled]:hover, .btn-next[disabled]:hover {
              background-color: transparent;
            }

            .btn-prev.is-active, .btn-next.is-active, .el-pager li.is-active {
              font-weight: 400;
              background-color: var(--el-fill-color-darker);
              color: var(--el-color-primary);
            }
          }
        }
      }
    }

    .content {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100%;
      transition: margin-left 0.3s;

      .upload-view {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 100%;

        .background {
          position: absolute;
          height: 70%;
          width: 70%;
          background-image: url("@/assets/images/bg.png");
          background-size: cover;
          background-repeat: no-repeat;
          // 在暗色主题下隐藏背景
          [data-theme="dark"] & {
            display: none;
          }
        }

        .upload {
          text-align: center;
          width: 50%;
          z-index: 1;

          h1 {
            margin-bottom: 40px;
            color: var(--el-text-color-primary);
          }

          :deep(.el-upload) {
            .el-upload-dragger {
              background-color: var(--el-fill-color-lighter);
              border-color: var(--el-border-color-light);
              box-shadow: 0 4px 40px 2px #12131608;
              border-radius: 24px;
              height: 280px;
            }

            .el-upload-dragger:hover {
              border-color: var(--el-color-primary-light-3);
            }

            .upload-text {
              color: var(--el-text-color-primary);
              font-size: 18px;
              font-weight: 600;
              margin-bottom: 12px;
            }

            p {
              font-size: 12px;
              margin-bottom: 2px;
              color: var(--el-text-color-secondary);
            }

            .el-button {
              height: 36px;
              border-radius: 8px;
              padding: 4px 12px;
              line-height: 20px;
              color: var(--el-text-color-primary);
              margin-top: 24px;
              border: 1px solid var(--el-border-color-lighter);
            }

            .el-button:hover {
              background-color: var(--el-fill-color-light);
            }
          }
        }
      }

      .result-view {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;

        .file-tabs {
          display: flex;
          align-items: center;
          padding: 0 16px;
          height: 48px;
          border-bottom: 1px solid var(--el-border-color-light);
          background-color: var(--el-bg-color-page);

          .file-info {
            min-width: 100px;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-right: 20px;
            font-weight: 600;

            .filename {
              color: var(--el-text-color-primary);
            }
          }

          .tabs-container {
            display: flex;
            flex: 1;
            height: 100%;

            .tab-item {
              display: flex;
              align-items: center;
              height: 100%;
              padding: 0 16px;
              cursor: pointer;
              position: relative;
              border-right: 1px solid var(--el-border-color-light);

              .el-icon {
                margin-right: 8px;
              }

              .tab-actions {
                margin-left: 8px;

                .panel-toggle {
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  width: 24px;
                  height: 24px;
                  border-radius: 50%;
                  cursor: pointer;
                  border: 1px solid var(--el-border-color);
                  background-color: var(--el-fill-color-light);
                  color: var(--el-text-color-secondary);
                  transition: all 0.2s ease;

                  &.is-active {
                    background-color: var(--el-color-primary);
                    color: white;
                    border-color: var(--el-color-primary);
                  }

                  &:hover {
                    opacity: 0.8;
                  }
                }
              }

              &:hover {
                background-color: var(--el-fill-color-light);
              }

              &.active {
                color: var(--el-color-primary);

                &::after {
                  content: '';
                  position: absolute;
                  bottom: 0;
                  left: 0;
                  width: 100%;
                  height: 2px;
                  background-color: var(--el-color-primary);
                }
              }

              &.disabled {
                opacity: 0.5;
                pointer-events: none;

                .tab-actions {
                  pointer-events: auto;
                  opacity: 1;
                }
              }
            }
          }
        }

        .content-panels {
          display: flex;
          flex: 1;
          overflow: hidden;

          .panel {
            display: flex;
            flex-direction: column;
            flex: 1;
            border-right: 1px solid var(--el-border-color-light);
            transition: flex 0.3s;

            &:last-child {
              border-right: none;
            }

            .panel-header {
              display: flex;
              align-items: center;
              justify-content: space-between;
              height: 40px;
              padding: 0 16px;
              border-bottom: 1px solid var(--el-border-color-light);
              background-color: var(--el-fill-color-lighter);

              h3 {
                margin: 0;
                font-size: 14px;
                font-weight: 600;
                color: var(--el-text-color-primary);
              }

              .el-button {
                &.el-button--primary {
                  &:not(.is-disabled) {
                    background-color: var(--el-color-primary);
                    border-color: var(--el-color-primary);
                    color: #ffffff;

                    &:hover {
                      background-color: var(--el-color-primary-light-3);
                      border-color: var(--el-color-primary-light-3);
                    }
                  }
                }

                &.el-button--default {
                  &:not(.is-disabled) {
                    background-color: var(--el-fill-color-light);
                    border-color: var(--el-border-color);
                    color: var(--el-text-color-primary);

                    &:hover {
                      color: var(--el-color-primary);
                      border-color: var(--el-color-primary);
                    }
                  }
                }
              }
            }

            .panel-content {
              flex: 1;
              overflow: hidden;
              padding: 0;
              position: relative;

              .original-content {
                padding: 20px;
                font-family: system-ui, -apple-system, sans-serif;

                .loading-content {
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  justify-content: center;
                  height: 200px;
                  color: var(--el-text-color-secondary);

                  .el-icon {
                    font-size: 32px;
                    margin-bottom: 12px;
                  }
                }

                .file-text-content {
                  white-space: pre-wrap;
                  word-break: break-word;
                  line-height: 1.6;
                  padding: 16px;
                  background-color: var(--el-fill-color-light);
                  border-radius: 8px;
                  overflow: auto;
                  max-height: calc(100vh - 200px);
                  color: var(--el-text-color-primary);
                }
              }

              .result-iframe {
                width: 100%;
                height: 100%;
                border: none;
                display: block;
              }

              .chat-container {
                display: flex;
                flex-direction: column;
                height: 100%;

                .chat-messages {
                  flex: 1;
                  overflow-y: auto;
                  padding: 16px;
                  display: flex;
                  flex-direction: column;
                  gap: 16px;

                  .message {
                    display: flex;

                    &.user {
                      justify-content: flex-end;

                      .message-content {
                        background-color: var(--chat-user-bubble-bg, var(--el-color-primary-light-9));
                        color: var(--chat-user-bubble-text, var(--el-text-color-primary));
                        border-radius: 12px 12px 0 12px;
                      }
                    }

                    &.assistant {
                      justify-content: flex-start;

                      .message-content {
                        background-color: var(--chat-assistant-bubble-bg, var(--el-fill-color-light));
                        color: var(--chat-assistant-bubble-text, var(--el-text-color-primary));
                        border-radius: 12px 12px 12px 0;

                        &.thinking {
                          padding: 12px 20px;
                        }
                      }
                    }

                    &.system {
                      display: none;
                    }

                    .avatar {
                      width: 36px;
                      height: 36px;
                      border-radius: 50%;
                      display: flex;
                      align-items: center;
                      justify-content: center;
                      margin: 0 8px;

                      &.user-avatar {
                        background-color: var(--el-color-primary);
                        color: white;
                      }

                      &.assistant-avatar {
                        background-color: var(--el-color-success);
                        color: white;
                      }
                    }

                    .message-content {
                      max-width: 70%;
                      padding: 12px 16px;
                      line-height: 1.5;
                      white-space: pre-wrap;
                      word-break: break-word;

                      .thinking-indicator {
                        display: flex;
                        gap: 4px;

                        span {
                          width: 8px;
                          height: 8px;
                          border-radius: 50%;
                          background-color: var(--el-text-color-secondary);
                          animation: pulse 1.5s infinite;

                          &:nth-child(2) {
                            animation-delay: 0.2s;
                          }

                          &:nth-child(3) {
                            animation-delay: 0.4s;
                          }
                        }
                      }

                      .answer {
                        margin-bottom: 8px;
                        line-height: 1.6;
                      }

                      .material {
                        margin-top: 12px;
                        padding: 8px 12px;
                        background-color: var(--el-fill-color-light);
                        border-radius: 6px;

                        .material-title {
                          font-size: 12px;
                          color: var(--el-text-color-secondary);
                          margin-bottom: 4px;
                        }

                        .material-content {
                          font-size: 13px;
                          color: var(--el-text-color-regular);
                          line-height: 1.5;
                          white-space: pre-wrap;
                        }
                      }
                    }
                  }
                }

                .chat-input {
                  padding: 16px;
                  border-top: 1px solid var(--el-border-color-light);
                  display: flex;
                  gap: 12px;

                  :deep(.el-textarea) {
                    .el-textarea__inner {
                      background-color: var(--el-fill-color-dark);
                      border-color: var(--el-border-color);
                      color: var(--el-text-color-primary);

                      &:hover {
                        border-color: var(--el-border-color-darker);
                      }

                      &:focus {
                        border-color: var(--el-color-primary);
                        background-color: var(--el-fill-color-darker);
                      }

                      &::placeholder {
                        color: var(--el-text-color-secondary);
                      }
                    }
                  }

                  .el-button {
                    align-self: flex-end;
                  }
                }
              }
            }
          }
        }
      }

      .history-icon {
        cursor: pointer;
        position: fixed;
        top: 32px;
        right: 48px;
        padding: 8px;
        background-color: var(--el-fill-color-light);
        border-radius: 8px;
      }

      .history-icon:hover {
        background-color: var(--el-fill-color-dark);
      }
    }
  }

  :deep(.main-content > div:first-of-type) {
    position: absolute !important;
    z-index: 0 !important;
  }
}

.history-header {
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 600;
  padding: 0 24px;
  margin: 16px 0;
}

.history-content {
  padding: 0 16px;
  margin-bottom: 16px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.5;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

.tab-item {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 16px;
  cursor: pointer;
  position: relative;
  border-right: 1px solid var(--el-border-color-light);

  .el-icon {
    margin-right: 8px;
  }

  .tab-actions {
    margin-left: 8px;

    .panel-toggle {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      cursor: pointer;
      border: 1px solid var(--el-border-color);
      background-color: var(--el-fill-color-light);
      color: var(--el-text-color-secondary);
      transition: all 0.2s ease;

      &.is-active {
        background-color: var(--el-color-primary);
        color: white;
        border-color: var(--el-color-primary);
      }

      &:hover {
        opacity: 0.8;
      }
    }
  }

  &:hover {
    background-color: var(--el-fill-color-light);
  }

  &.active {
    color: var(--el-color-primary);

    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 2px;
      background-color: var(--el-color-primary);
    }
  }

  &.disabled {
    opacity: 0.5;
    pointer-events: none;

    .tab-actions {
      pointer-events: auto;
      opacity: 1;
    }
  }
}

.panel-toggle-btn {
  /* 确保按钮始终显示 */
  display: flex !important;
  align-items: center;
  justify-content: center;
}

.knowledge-graph-content {
  height: 100%;
  overflow: hidden;

  .result-iframe {
    width: 100%;
    height: 100%;
    border: none;
    display: block;
    background-color: white;
  }
}

.theme-header {
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 600;
  padding: 0 24px;
  margin: 16px 0;
}

.theme-content {
  padding: 0 16px;
  margin-bottom: 16px;

  .theme-item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    cursor: pointer;
    border-radius: 6px;
    margin-bottom: 8px;
    transition: all 0.3s ease;
    color: var(--el-text-color-primary);

    &:hover {
      background-color: var(--el-fill-color-light);
    }

    &.active {
      background-color: var(--el-fill-color-light);
      color: var(--el-color-primary);
    }

    .theme-preview {
      width: 24px;
      height: 24px;
      border-radius: 4px;
      margin-right: 12px;
      border: 1px solid var(--el-border-color);
      flex-shrink: 0;

      &.default {
        background-color: #ffffff;
      }

      &.dark {
        background-color: #1a1a1a;
        border-color: #ffffff;
      }

      &.blue {
        background-color: #409eff;
      }

      &.green {
        background-color: #67c23a;
      }
    }

    span {
      font-size: 14px;
    }
  }
}

// 自定义弹出框样式
:deep(.el-popover.custom-popover) {
  padding: 0 0 12px 0;
  border-radius: 8px;

  [data-theme="dark"] & {
    background-color: #2b2b2b;
    border: 1px solid #3a3a3a;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
}

// 修改暗色主题下的样式
[data-theme="dark"] {
  .file-item {
    &.active {
      background-color: var(--el-bg-color) !important;
      border-color: var(--el-border-color-light);
    }

    &.can-click.active:hover {
      border-color: var(--el-color-primary-light-3);
    }

    .delete-action {
      .delete-icon {
        filter: invert(1); // 反转SVG颜色
        opacity: 0.4;

        &:hover {
          opacity: 0.8;
          background-color: var(--el-color-danger-light-3);
        }
      }
    }
  }

  // 主题切换界面样式
  .theme-header {
    color: #e5e5e5;
    border-bottom: 1px solid #3a3a3a;
    background-color: #2b2b2b;
    margin: 0;
    padding: 16px 24px;
  }

  .theme-content {
    background-color: #2b2b2b;

    .theme-item {
      color: #b0b0b0;
      transition: all 0.3s ease;

      &:hover {
        background-color: #363636;
        color: #e5e5e5;
      }

      &.active {
        background-color: #363636;
        color: var(--el-color-primary);
      }

      .theme-preview {
        border-color: #4a4a4a;

        &.dark {
          border-color: #5a5a5a;
        }
      }

      span {
        font-size: 14px;
        font-weight: 500;
      }
    }
  }
}

// 添加过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

// 暗色主题适配
[data-theme="dark"] {
  .file-item {
    &.active {
      background-color: var(--el-bg-color) !important;
      border-color: var(--el-border-color-light);
    }

    &.can-click.active:hover {
      border-color: var(--el-color-primary-light-3);
    }
  }
}

// 添加其他主题的适配
[data-theme="blue"], [data-theme="green"] {
  .file-item {
    &.active {
      background-color: var(--el-bg-color) !important;
      border-color: var(--el-border-color);
    }

    &.can-click.active:hover {
      border-color: var(--el-color-primary);
    }
  }
}

.filter-content {
  padding: 16px;

  .filter-section {
    margin-bottom: 20px;

    .filter-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--el-text-color-primary);
      margin-bottom: 12px;
    }

    .filter-options {
      .el-radio-group {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
    }
  }

  .filter-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color-light);
  }
}
</style>
