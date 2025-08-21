<script setup>
import SideBar from "./components/SideBar.vue";
import {ref, reactive, onMounted, watch, nextTick} from "vue";
import SvgIcon from "@/components/SvgIcon/index.vue";
import {Link, Document, Loading, SuccessFilled, Download, ChatDotRound, Tickets, View, Hide, ArrowDown} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';
import { themes, applyTheme } from '@/styles/theme';

const sideBarRef = ref();
const fileListExpand = ref(false);
const isSearch = ref(false);
const searchValue = ref('');
const uploadFileList = ref([]);
const filteredFileList = ref([]);

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
]);
const userInput = ref('');
const chatLoading = ref(false);
const currentChatFile = ref(null); // 当前正在聊天的文件
const abortController = ref(null); // 用于取消请求的控制器
const fileChatStates = ref({}); // 存储每个文件的聊天状态

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

// 添加RAG流式输出开关设置
const enableStreamOutput = ref(false);
// 添加PDF图片文本识别设置
const useImg2txt = ref(false);
// 添加笔记类型设置
const noteType = ref('general');

// 保存和获取流式输出设置
const saveStreamSetting = () => {
  localStorage.setItem('rag-stream-output', enableStreamOutput.value ? 'true' : 'false');
};

// 保存图片文本识别设置
const saveImg2txtSetting = () => {
  localStorage.setItem('use-img2txt', useImg2txt.value ? 'true' : 'false');
};

// 自动滚动到底部功能
const chatMessagesContainer = ref(null);
const showScrollButton = ref(false);
const autoScroll = ref(true);

// 添加流式处理状态变量
const streamingStatus = ref('');

// 监听聊天消息区域的滚动事件
const handleChatScroll = () => {
  if (!chatMessagesContainer.value) return;

  const container = chatMessagesContainer.value;
  const isScrolledToBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;

  // 只有当用户手动上滑时才禁用自动滚动
  if (!isScrolledToBottom && !chatLoading.value) {
    autoScroll.value = false;
    showScrollButton.value = true;
  } else if (isScrolledToBottom) {
    autoScroll.value = true;
    showScrollButton.value = false;
  }
};

// 滚动到底部函数
const scrollToBottom = () => {
  if (!chatMessagesContainer.value) return;

  nextTick(() => {
    chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
    autoScroll.value = true;
    showScrollButton.value = false;
  });
};

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

// 格式化文本，确保正确显示换行符
const formatTextWithLineBreaks = (text) => {
  if (!text) return '';
  if (Array.isArray(text)) {
    return text.join('\n');
  }
  return text;
};

// 从localStorage加载聊天历史
const loadChatHistory = (filename) => {
  if (!filename) return;
  
  try {
    const savedChat = localStorage.getItem(`chat_${filename}`);
    if (savedChat) {
      const parsed = JSON.parse(savedChat);
      // 确保内容格式正确
      chatMessages.value = parsed.map(msg => {
        if (msg.role === 'assistant' && typeof msg.content === 'object') {
          return {
            ...msg,
            content: {
              answer: formatTextWithLineBreaks(msg.content.answer),
              material: formatTextWithLineBreaks(msg.content.material)
            }
          };
        }
        return msg;
      });
    } else {
      chatMessages.value = [];
    }
  } catch (error) {
    console.error('加载聊天历史失败:', error);
    chatMessages.value = [];
  }
};

// 页面加载时获取历史文件列表
onMounted(async () => {
  try {
    // 初始化主题
    const savedTheme = localStorage.getItem('app-theme') || 'default';
    changeTheme(savedTheme);

    // 加载流式输出设置
    const savedStreamSetting = localStorage.getItem('rag-stream-output');
    enableStreamOutput.value = savedStreamSetting === 'true';

    // 加载图片文本识别设置
    const savedImg2txtSetting = localStorage.getItem('use-img2txt');
    useImg2txt.value = savedImg2txtSetting === 'true';
    
    const response = await axios.get('http://localhost:8000/list-files');
    if (response.data && Array.isArray(response.data.files)) {
      // 将历史文件添加到文件列表，保持原始文件名和状态
      uploadFileList.value = response.data.files.map(file => ({
        name: file.filename || file.name || file,  // 保持原始文件名
        status: file.status || 'completed',
        display_status: file.display_status || (file.status ? getStatusText(file.status) : '已完成'),
        size: file.size || 0,
        percentage: 100
      }));

      // 初始化过滤后的文件列表
      filteredFileList.value = [...uploadFileList.value];

      // 检查是否有未完成的文件
      uploadFileList.value.forEach(file => {
        // 包括所有处理中状态
        const processingStatuses = [
          'uploading', 'processing'
        ];

        if (processingStatuses.includes(file.status)) {
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

    // 清理聊天状态
    if (fileChatStates.value[file.name]) {
      delete fileChatStates.value[file.name];
    }

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

// 删除RAG历史记录功能
const deleteRagHistory = async (file, event) => {
  // 阻止事件冒泡，防止触发文件查看
  event.stopPropagation();
  
  try {
    // 添加确认弹窗
    await ElMessageBox.confirm(
        `确定要清除文件 ${file.name} 的RAG聊天记录吗？此操作不会删除文件和知识图谱。`,
        '清除RAG历史',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
    );

    // 调用后端API删除RAG历史
    await axios.delete(`http://localhost:8000/rag-history/${file.name}`);
    
    // 清理本地缓存
    localStorage.removeItem(`chat_${file.name}`);  // 删除本地聊天记录

    // 清理聊天状态
    if (fileChatStates.value[file.name]) {
      delete fileChatStates.value[file.name];
    }

    // 如果当前正在查看该文件的RAG，清空聊天消息
    if (currentFile.value && currentFile.value.name === file.name) {
      chatMessages.value = [];
    }

    ElMessage.success(`文件 ${file.name} 的RAG历史记录已清除`);
  } catch (error) {
    if (error !== 'cancel') {  // 如果不是用户取消操作
      console.error('清除RAG历史记录失败:', error);
      ElMessage.error('清除RAG历史记录失败');
    }
  }
};

// 添加停止RAG回答的函数
const stopRagResponse = () => {
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
    chatLoading.value = false;
    // 移除正在思考的消息
    chatMessages.value = chatMessages.value.filter(msg => !msg.thinking);
    ElMessage.info('已停止回答');
  }
};

// 处理流式输出的函数 - 使用 EventSource
const processStreamResponse = async (url, data, messageIndex) => {
  try {
    chatLoading.value = true;
    streamingStatus.value = '准备连接...';

    // 创建一个新的AbortController
    abortController.value = new AbortController();

    // 直接以POST方式发送数据
    const postResponse = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      signal: abortController.value.signal
    });

    if (!postResponse.ok) {
      const errorText = await postResponse.text();
      throw new Error(`HTTP error! status: ${postResponse.status}, message: ${errorText}`);
    }

    streamingStatus.value = '已连接，等待响应...';
    const reader = postResponse.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    // 开始读取流数据
    while (true) {
      if (!abortController.value) break; // 如果已中断，退出循环

      const { done, value } = await reader.read();
      if (done) break;

      // 解码收到的数据
      buffer += decoder.decode(value, { stream: true });

      // 处理SSE格式的数据
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || ''; // 最后一行可能不完整，保留到下一次处理

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;

        try {
          const eventData = JSON.parse(line.substring(6));

          // 根据不同类型的消息进行处理
          if (eventData.type === 'status') {
            // 在UI上显示当前处理状态
            streamingStatus.value = eventData.content;
          }
          else if (eventData.type === 'content') {
            // 更新聊天内容
            if (messageIndex !== -1 && chatMessages.value[messageIndex]) {
              // 确保正确处理换行符
              let formattedContent = eventData.full;
              // 如果内容是字符串数组，用换行符连接
              if (Array.isArray(formattedContent)) {
                formattedContent = formattedContent.join('\n');
              }
              chatMessages.value[messageIndex].content.answer = formattedContent;

              // 自动滚动到底部
              if (autoScroll.value) {
                scrollToBottom();
              }
            }
          }
          else if (eventData.type === 'final') {
            // 接收最终结果，包括答案和参考资料
            if (messageIndex !== -1 && chatMessages.value[messageIndex]) {
              // 检查响应内容是否为JSON格式
              let finalAnswer = eventData.answer;
              let finalMaterial = eventData.material;
              
              // 使用正则表达式匹配```json和```之间的内容
              const jsonRegex = /```json\s*([\s\S]*?)\s*```/;
              
              
              if (typeof finalAnswer === 'string') {
                const jsonMatch = finalAnswer.match(jsonRegex);
                if (jsonMatch && jsonMatch[1]) {
                  try {
                    const jsonContent = JSON.parse(jsonMatch[1]);
                    if (jsonContent.answer) {
                      // 如果answer是数组，则将其连接为字符串
                      if (Array.isArray(jsonContent.answer)) {
                        finalAnswer = jsonContent.answer.join('\n');
                      } else {
                        finalAnswer = jsonContent.answer;
                      }
                    }
                    
                    // 检查material是否存在且非空
                    if (jsonContent.material) {
                      if (Array.isArray(jsonContent.material) && jsonContent.material.length > 0) {
                        finalMaterial = jsonContent.material.join('\n');
                      } else if (typeof jsonContent.material === 'string' && jsonContent.material.trim() !== '') {
                        finalMaterial = jsonContent.material;
                      } else {
                        finalMaterial = '';
                      }
                    } else {
                      finalMaterial = '';
                    }
                  } catch (e) {
                    console.warn('无法解析JSON代码块内容:', e);
                  }
                } else if (finalAnswer.trim().startsWith('{') && finalAnswer.trim().endsWith('}')) {
                  // 尝试直接解析可能的JSON字符串
                  try {
                    const jsonContent = JSON.parse(finalAnswer);
                    if (jsonContent.answer) {
                      if (Array.isArray(jsonContent.answer)) {
                        finalAnswer = jsonContent.answer.join('\n');
                      } else {
                        finalAnswer = jsonContent.answer;
                      }
                    }
                    
                    if (jsonContent.material) {
                      if (Array.isArray(jsonContent.material) && jsonContent.material.length > 0) {
                        finalMaterial = jsonContent.material.join('\n');
                      } else if (typeof jsonContent.material === 'string' && jsonContent.material.trim() !== '') {
                        finalMaterial = jsonContent.material;
                      } else {
                        finalMaterial = '';
                      }
                    } else {
                      finalMaterial = '';
                    }
                  } catch (e) {
                    console.warn('无法解析answer中的JSON内容:', e);
                  }
                }
              }
              
              // 更新聊天消息
              chatMessages.value[messageIndex].content.answer = finalAnswer;
              if (finalMaterial && finalMaterial.trim() !== '') {
                chatMessages.value[messageIndex].content.material = finalMaterial;
              } else {
                // 如果material为空则不显示
                chatMessages.value[messageIndex].content.material = '';
              }
              chatMessages.value[messageIndex].streaming = false;

              // 自动滚动到底部
              if (autoScroll.value) {
                scrollToBottom();
              }

              // 保存聊天记录到localStorage
              if (currentFile.value?.name) {
                const chatHistory = chatMessages.value.filter(msg => !msg.thinking && !msg.streaming);
                localStorage.setItem(`chat_${currentFile.value.name}`, JSON.stringify(chatHistory));
              }
            }
          }
          else if (eventData.type === 'error') {
            // 处理错误
            console.error('Stream error:', eventData.content);
            ElMessage.error(eventData.content || '获取回复失败');
          }
          else if (eventData.type === 'done') {
            // 处理完成
            // console.log('Stream completed');
            streamingStatus.value = '';
            break;
          }
        } catch (e) {
          console.error('Error parsing SSE data:', e, line);
        }
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      // 请求被中断，不处理
      console.log('Stream aborted by user');
      streamingStatus.value = '已停止生成';
      setTimeout(() => {
        streamingStatus.value = '';
      }, 2000);
      return;
    }

    console.error('流式输出处理失败:', error);
    ElMessage.error(error.message || '获取回复失败');
    streamingStatus.value = '';

    // 移除流式输出消息
    if (messageIndex !== -1 && chatMessages.value[messageIndex]) {
      chatMessages.value.splice(messageIndex, 1);
    }
  } finally {
    chatLoading.value = false;
    abortController.value = null;
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

  // 如果切换了文件，保存当前文件的聊天记录
  if (currentChatFile.value && currentChatFile.value !== currentFile.value.name) {
    const chatHistory = chatMessages.value.filter(msg => !msg.thinking && !msg.streaming);
    localStorage.setItem(`chat_${currentChatFile.value}`, JSON.stringify(chatHistory));
  }

  // 更新当前聊天文件
  currentChatFile.value = currentFile.value.name;

  chatMessages.value.push({ role: 'user', content: userInput.value });
  const currentQuestion = userInput.value;
  userInput.value = '';
  chatLoading.value = true;

  // 处理历史消息，确保格式正确
  const historyMessages = chatMessages.value
      .filter(msg => !msg.thinking && !msg.streaming && msg.role !== 'system')
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

  // 添加思考中的消息或初始化流式输出的容器
  if (enableStreamOutput.value) {
    // 流式输出模式，显示初始化的空消息
    chatMessages.value.push({
      role: 'assistant',
      content: {
        answer: '',
        material: ''
      },
      streaming: true // 标记为流式输出中
    });

    // 启用自动滚动
    autoScroll.value = true;
    // 自动滚动到底部
    scrollToBottom();

    // 使用流式处理函数，连接到新的流式端点
    const streamingIndex = chatMessages.value.length - 1;
    await processStreamResponse('http://localhost:8000/hybridrag/stream', {
      request: currentQuestion,
      model: 'deepseek',
      flow: true,
      filename: currentFile.value.name,
      messages: enableHistoryContext.value ? historyMessages : null
    }, streamingIndex);
  } else {
    // 非流式输出模式
    // 添加思考中的消息
    chatMessages.value.push({ role: 'assistant', content: '思考中...', thinking: true });

    // 启用自动滚动
    autoScroll.value = true;
    // 自动滚动到底部
    scrollToBottom();

    try {
      const response = await axios.post('http://localhost:8000/hybridrag', {
        request: currentQuestion,
        model: 'deepseek',
        flow: false,
        filename: currentFile.value.name,
        messages: enableHistoryContext.value ? historyMessages : null
      }, {
        signal: abortController.value ? abortController.value.signal : undefined
      });

      // 检查响应是否有效
      if (!response || !response.data) {
        throw new Error('服务器响应无效');
      }

      // 检查响应状态
      if (response.data.status === 'processing') {
        ElMessage.warning('文件正在处理中，请稍后再试');
        chatMessages.value = chatMessages.value.filter(msg => !msg.thinking && !msg.streaming);
        return;
      } else if (response.data.status === 'error') {
        ElMessage.error(response.data.message || '文件处理失败');
        chatMessages.value = chatMessages.value.filter(msg => !msg.thinking && !msg.streaming);
        return;
      }

      // 检查结果是否存在
      if (!response.data.result) {
        throw new Error('服务器返回结果为空');
      }

      // 非流式输出模式，替换"思考中"的消息
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

      // 如果启用自动滚动，自动滚到最新消息
      if (autoScroll.value) {
        scrollToBottom();
      }

      // 保存聊天记录到localStorage
      if (currentFile.value?.name) {
        const chatHistory = chatMessages.value.filter(msg => !msg.thinking && !msg.streaming);
        localStorage.setItem(`chat_${currentFile.value.name}`, JSON.stringify(chatHistory));
      }
    } catch (error) {
      if (error.name === 'CanceledError' || error.name === 'AbortError') {
        // 请求被取消，不需要显示错误信息
        return;
      }
      console.error('获取RAG回复失败:', error);
      chatMessages.value = chatMessages.value.filter(msg => !msg.thinking && !msg.streaming);
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
      abortController.value = null;

      // 如果启用自动滚动，自动滚到最新消息
      if (autoScroll.value) {
        scrollToBottom();
      }
    }
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
const beforeUpload = async (file) => {
  // 检查文件是否已存在
  const existingFile = uploadFileList.value.find(item => item.name === file.name);
  
  if (existingFile) {
    // 询问用户是否要覆盖已存在的文件
    try {
      await ElMessageBox.confirm(
        `文件 "${file.name}" 已存在，是否要进行增量更新？`,
        '文件已存在',
        {
          confirmButtonText: '增量更新',
          cancelButtonText: '取消上传',
          type: 'warning',
        }
      );
      
      // 用户确认更新，修改原文件状态为更新中
      existingFile.status = 'updating';
      existingFile.display_status = '增量更新中';
      existingFile.percentage = 0;
      existingFile.isUpdate = true; // 标记为增量更新
      return true;
    } catch (e) {
      // 用户取消上传
      return false;
    }
  }
  
  // 新文件，正常上传
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
    // 判断是否为增量更新
    if (targetFile.isUpdate) {
      // 更新状态为增量更新处理中
      targetFile.status = 'updating';
      targetFile.display_status = '增量更新中';
      targetFile.percentage = 100;
      targetFile.resultId = response.resultId || Date.now();
    } else {
      // 新文件，修改状态为处理中
      targetFile.status = 'processing';
      targetFile.display_status = '处理中';
      targetFile.percentage = 100;
      targetFile.resultId = response.resultId || Date.now();
    }

    // 开始检查处理状态
    checkFileProcessingStatus(targetFile);
  }
}

// 添加检查文件处理状态的函数
const checkFileProcessingStatus = async (file) => {
  try {
    // 文件名
    const filename = file.name;
    const checkInterval = 3000; // 检查间隔（毫秒）

    // 第一次立即检查
    await updateFileStatus(file);

    // 持续检查直到处理完成或失败
    const intervalId = setInterval(async () => {
      const updated = await updateFileStatus(file);

      // 如果状态是completed或error，停止检查
      if (updated && (file.status === 'completed' || file.status === 'error')) {
        clearInterval(intervalId);
      }
    }, checkInterval);

    // 10分钟后强制停止检查
    setTimeout(() => {
      clearInterval(intervalId);
    }, 10 * 60 * 1000);
  } catch (error) {
    console.error('检查文件处理状态失败:', error);
  }
};

// 添加一个更新文件状态的函数
const updateFileStatus = async (file) => {
  try {
    const response = await axios.get(`http://localhost:8000/processing-status/${file.name}`);
    if (response.data) {
      // 更新文件状态
      file.status = response.data.status;
      if (response.data.display_status) {
        file.display_status = response.data.display_status;
      } else {
        file.display_status = getStatusText(response.data.status);
      }
      
      // 如果文件存在增量更新标记并且状态已变为completed，清除更新标记
      if (file.isUpdate && response.data.status === 'completed') {
        file.isUpdate = false;
      }
      
      return true;
    }
    return false;
  } catch (error) {
    console.error('获取文件状态失败:', error);
    return false;
  }
};

const onUploadError = (error, file) => {
  const targetFile = uploadFileList.value.find(item => item.name === file.name);
  if (targetFile) {
    targetFile.status = 'error';
    ElMessage.error(`文件 ${file.name} 上传失败`);
  }
}

// 添加handleSearch函数，这个函数在搜索框输入时被调用，但之前未定义
const handleSearch = () => {
  handleFilter();
};

// 查看文件结果
const viewFileResult = async (file) => {
  if (file.status === 'completed') {
    try {
      // 如果切换了文件，保存当前文件的聊天记录
      if (currentChatFile.value && currentChatFile.value !== file.name) {
        const chatHistory = chatMessages.value.filter(msg => !msg.thinking);
        localStorage.setItem(`chat_${currentChatFile.value}`, JSON.stringify(chatHistory));
      }

      // 如果当前有正在进行的请求，取消它
      if (abortController.value) {
        abortController.value.abort();
        abortController.value = null;
        chatLoading.value = false;
      }

      activeView.value = 'result';
      currentFile.value = file;
      currentChatFile.value = file.name;

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

      // 使用新函数加载聊天历史记录
      loadChatHistory(file.name);

      // 启用自动滚动
      autoScroll.value = true;
      
      // 不管当前是什么标签，先切换到RAG标签
      activeTab.value = 'rag';
      
      // 使用nextTick确保DOM已更新
      nextTick(() => {
        scrollToBottom();
      });
    } catch (error) {
      console.error('查看文件结果失败:', error);
      ElMessage.error('查看文件结果失败');
    }
  } else if (file.status === 'error') {
    // 处理错误状态的文件，提示用户是否重新构建
    try {
      await ElMessageBox.confirm(
        `文件 ${file.name} 处理失败，是否重新开始构建知识图谱？`,
        '重新构建',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
      );
      
      // 重新上传文件
      rebuildKnowledgeGraph(file);
    } catch (error) {
      if (error !== 'cancel') {
        console.error('操作被取消或发生错误:', error);
      }
    }
  } else {
    // 对于uploading、processing等状态，只显示提示
    ElMessage.info(`文件 ${file.name} 正在${file.display_status || getStatusText(file.status)}，请稍后查看`);
  }
};

// 添加重新构建知识图谱函数
const rebuildKnowledgeGraph = async (file) => {
  try {
    // 更新文件状态为正在上传
    const targetFile = uploadFileList.value.find(item => item.name === file.name);
    if (targetFile) {
      targetFile.status = 'uploading';
      targetFile.display_status = '重新上传中';
      targetFile.percentage = 0;
    }
    
    // 使用新的rebuild API端点
    const formData = new FormData();
    formData.append('filename', file.name);
    formData.append('noteType', noteType.value);
    // 显式使用字符串值
    const img2txtValue = useImg2txt.value ? 'true' : 'false';
    formData.append('use_img2txt', img2txtValue);
    
    console.log('重建使用的参数:', {
      filename: file.name,
      noteType: noteType.value, 
      use_img2txt: img2txtValue,
      useImg2txt原始值: useImg2txt.value
    });
    
    // 发送重新构建请求
    const response = await axios.post('http://localhost:8000/rebuild', formData);
    
    // 处理响应
    if (response.data) {
      if (targetFile) {
        targetFile.status = 'processing';
        targetFile.display_status = '处理中';
        targetFile.percentage = 100;
      }
      
      // 开始检查处理状态
      checkFileProcessingStatus(targetFile);
      
      ElMessage.success(`文件 ${file.name} 重新构建已开始`);
    }
  } catch (error) {
    console.error('重新构建失败:', error);
    ElMessage.error(`重新构建失败: ${error.message || '未知错误'}`);
    
    // 恢复文件状态为错误
    const targetFile = uploadFileList.value.find(item => item.name === file.name);
    if (targetFile) {
      targetFile.status = 'error';
      targetFile.display_status = '失败';
    }
  }
};

// 关闭结果视图
const closeResultView = () => {
  // 如果当前有正在进行的请求，取消它
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
    chatLoading.value = false;
  }

  if (currentChatFile.value) {
    // 过滤掉思考中和流式输出中的消息
    const chatHistory = chatMessages.value.filter(msg => !msg.thinking && !msg.streaming);
    localStorage.setItem(`chat_${currentChatFile.value}`, JSON.stringify(chatHistory));
  }
  activeView.value = 'upload';
  knowledgeGraphData.value = null;
  currentChatFile.value = null;
  chatMessages.value = [];
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

    // 在切换到rag标签时，自动滚动到最新消息
    if (tab === 'rag') {
      nextTick(() => {
        scrollToBottom();
      });
    }
  }
};

// 获取文件状态的文本描述
const getStatusText = (status) => {
  switch (status) {
    case 'uploading':
      return '上传中';
    case 'processing':
      return '处理中';
    case 'updating':
      return '增量更新中';
    case 'completed':
      return '已完成';
    case 'error':
      return '处理失败';
    default:
      return status;
  }
};

// 获取文件状态对应的图标
const getFileIcon = (status) => {
  switch (status) {
    case 'uploading':
    case 'processing':
    case 'updating':
      return Loading;
    case 'completed':
      return SuccessFilled;
    case 'error':
      return 'circle-close';
    default:
      return Document;
  }
};

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

// 查看文件内容
const viewFile = (file) => {
  if (!file || !file.name || file.status !== 'completed') return;
  
  currentFile.value = file;
  activeView.value = 'result';
  activeTab.value = 'original';
  
  // 使用新的函数加载聊天历史
  loadChatHistory(file.name);
  
  // ...其他代码
};

// 准备文件的聊天状态
const prepareChatState = (file) => {
  // 首先尝试从localStorage加载聊天记录
  const savedChat = localStorage.getItem(`chat_${file.name}`);
  
  if (savedChat) {
    // 如果localStorage中有聊天记录，使用它
    chatMessages.value = JSON.parse(savedChat);
    
    // 同时更新fileChatStates中的记录
    if (!fileChatStates.value[file.name]) {
      fileChatStates.value[file.name] = {
        messages: JSON.parse(savedChat),
        lastActive: new Date().getTime()
      };
    } else {
      fileChatStates.value[file.name].messages = JSON.parse(savedChat);
      fileChatStates.value[file.name].lastActive = new Date().getTime();
    }
  } else {
    // 如果localStorage中没有聊天记录，检查fileChatStates
    if (!fileChatStates.value[file.name]) {
      // 如果fileChatStates中也没有，创建新的聊天记录
      fileChatStates.value[file.name] = {
        messages: [
          { role: 'system', content: `我是基于文档《${file.name}》的HybridRAG助手，可以回答与文档相关的问题。` }
        ],
        lastActive: new Date().getTime()
      };
      
      // 更新聊天消息
      chatMessages.value = [...fileChatStates.value[file.name].messages];
    } else {
      // 如果fileChatStates中有记录，使用它
      fileChatStates.value[file.name].lastActive = new Date().getTime();
      chatMessages.value = [...fileChatStates.value[file.name].messages];
    }
  }

  // 设置当前聊天文件
  currentChatFile.value = file;

  // 如果切换到RAG标签，自动滚动到底部
  if (activeTab.value === 'rag') {
    nextTick(() => {
      scrollToBottom();
    });
  }
};

// 加载文件内容
const loadFileContent = async (file) => {
  fileContentLoading.value = true;
  fileContent.value = '';

  try {
    const response = await axios.get(`http://localhost:8000/file-content/${file.name}`);
    if (response.data && response.data.content) {
      fileContent.value = response.data.content;
    }
  } catch (error) {
    console.error('获取文件内容失败:', error);
    ElMessage.warning('获取文件内容失败');
  } finally {
    fileContentLoading.value = false;
  }
};

// 加载知识图谱
const loadKnowledgeGraph = async (file) => {
  if (!file || !file.name) return;

  try {
    knowledgeGraphLoading.value = true;
    await fetchKnowledgeGraph(file.name);
  } catch (error) {
    console.error('加载知识图谱失败:', error);
    ElMessage.warning('加载知识图谱失败');
  } finally {
    knowledgeGraphLoading.value = false;
  }
};

// 添加历史上下文相关状态
const enableHistoryContext = ref(true);

const onUploadClick = () => {
  const formData = new FormData();
  formData.append('file', uploadRef.value.files[0]);
  formData.append('noteType', noteType.value);
  
  axios.post('/api/upload', formData, {
    onUploadProgress: (e) => {
      onUploadProgress(e, uploadRef.value.files[0]);
    }
  }).then(response => {
    onUploadSuccess(response.data, uploadRef.value.files[0]);
  }).catch(error => {
    onUploadError(error, uploadRef.value.files[0]);
  });
}

// 修改onUploadSuccess函数，处理noteType参数
// ... existing code ...

// 修改onBeforeUpload函数，添加调试信息
const onBeforeUpload = async (file) => {
  try {
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', file);
    formData.append('noteType', noteType.value);
    
    // 使用open/off字符串表示开关状态
    const img2txtValue = useImg2txt.value ? 'open' : 'off';
    formData.append('use_img2txt', img2txtValue);
    
    console.log('上传参数:', {
      file: file.name,
      noteType: noteType.value,
      use_img2txt: img2txtValue
    });

    // 在上传前先检查文件是否已经存在，如果存在则执行更新操作
    const existingFile = uploadFileList.value.find(item => item.name === file.name);
    
    // 开始上传过程
    const response = await axios.post('http://localhost:8000/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        // 计算上传进度
        const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        
        // 更新上传进度
        const uploadingFile = uploadFileList.value.find(item => item.name === file.name);
        if (uploadingFile) {
          uploadingFile.percentage = percentage;
        }
      }
    });
  } catch (error) {
    console.error('上传文件失败:', error);
    ElMessage.error('上传文件失败');
  }
}
</script>

<template>
  <div class="main-container">
    <side-bar
        ref="sideBarRef"
        v-model:fileListExpand="fileListExpand"
        v-model:enableStreamOutput="enableStreamOutput"
        v-model:enableHistoryContext="enableHistoryContext"
        v-model:noteType="noteType"
        v-model:useImg2txt="useImg2txt"
        @update:enableStreamOutput="saveStreamSetting"
        @update:useImg2txt="saveImg2txtSetting"
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
                  'active': currentFile?.name === file.name,
                  'expanded': sideBarRef?.expandedFileId === file.name
                }"
              >
                <div class="file-header" 
                     @dblclick="viewFileResult(file)"
                     @click="sideBarRef?.toggleFileExpand(file)"
                     @mouseenter="currentFileId = file.name"
                     @mouseleave="currentFileId = null">
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
                      {{ file.display_status || getStatusText(file.status) }}
                    </div>
                    <transition name="fade">
                      <div v-if="currentFileId === file.name && file.status === 'completed'" class="delete-action">
                        <el-tooltip content="清除RAG历史" placement="top">
                          <img
                              src="@/assets/icons/svg/clear.svg"
                              alt="清除RAG历史"
                              class="clear-icon"
                              @click.stop="deleteRagHistory(file, $event)"
                          />
                        </el-tooltip>
                        <el-tooltip content="删除文件" placement="top">
                          <img
                              src="@/assets/icons/svg/delete.svg"
                              alt="删除"
                              class="delete-icon"
                              @click.stop="deleteFile(file)"
                          />
                        </el-tooltip>
                      </div>
                    </transition>
                  </div>
                </div>
                
                <!-- 展开的实体卡片 -->
                <div v-if="sideBarRef?.expandedFileId === file.name" class="file-entities-card">
                  <div v-if="sideBarRef?.loadingEntities[file.name]" class="loading-entities">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>加载主要实体中...</span>
                  </div>
                  <div v-else-if="sideBarRef?.fileEntities[file.name]?.errorMessage" class="entities-error">
                    <el-alert
                      :title="sideBarRef?.fileEntities[file.name]?.errorMessage"
                      type="error"
                      :closable="false"
                      size="small"
                      show-icon
                    />
                  </div>
                  <div v-else-if="sideBarRef?.fileEntities[file.name]?.entities?.length" class="entities-list">
                    <div class="entities-title">主要实体</div>
                    <div class="entities-content">
                      <el-tag
                        v-for="entity in sideBarRef?.fileEntities[file.name].entities"
                        :key="entity"
                        class="entity-tag"
                        size="small"
                        effect="plain"
                      >
                        {{ entity }}
                      </el-tag>
                    </div>
                  </div>
                  <div v-else class="no-entities">
                    <el-empty description="暂无实体数据" :image-size="60" />
                  </div>
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
            <h1>智能图谱笔记系统! 🎉</h1>
            <el-upload
                drag
                action="http://localhost:8000/upload"
                :data="() => ({ 
                  noteType: noteType, 
                  use_img2txt: useImg2txt ? 'true' : 'false'
                })"
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
              <p>支持的文件类型：TXT，PDF...</p>
              <p>单个txt不超过 5M</p>
              <p>图谱初始构造时间较长，请耐心等待</p>
              <br>
              <br>
              <p>作者：XIK</p>
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
                  <div class="chat-messages" ref="chatMessagesContainer" @scroll="handleChatScroll">
                    <div v-for="(message, index) in chatMessages" :key="index"
                         :class="['message', message.role, {'thinking': message.thinking, 'streaming': message.streaming}]">
                      <div v-if="message.role === 'user'" class="avatar user-avatar">
                        <span>U</span>
                      </div>
                      <div v-else-if="message.role === 'assistant'" class="avatar assistant-avatar">
                        <span>AI</span>
                      </div>
                      <div class="message-content" :class="{'thinking': message.thinking, 'streaming': message.streaming}">
                        <div v-if="message.thinking" class="thinking-indicator">
                          <span></span><span></span><span></span>
                        </div>
                        <div v-else-if="message.streaming" class="streaming-content">
                          <div class="answer" v-html="Array.isArray(message.content.answer) ? message.content.answer.join('\n') : message.content.answer"></div>
                          <div class="cursor-blink"></div>
                          <div v-if="streamingStatus" class="streaming-status">{{ streamingStatus }}</div>
                        </div>
                        <div v-else>
                          <template v-if="typeof message.content === 'object'">
                            <div class="answer" v-html="Array.isArray(message.content.answer) ? message.content.answer.join('\n') : message.content.answer"></div>
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

                  <div
                      v-if="showScrollButton"
                      class="scroll-to-bottom-btn"
                      @click="scrollToBottom"
                  >
                    <el-icon><ArrowDown /></el-icon>
                  </div>

                  <div class="chat-input">
                    <div class="input-actions">
                      <el-input
                          v-model="userInput"
                          type="textarea"
                          :autosize="{ minRows: 2, maxRows: 4 }"
                          placeholder="输入问题..."
                          :disabled="chatLoading"
                          @keyup.enter.ctrl="sendMessage"
                      />
                      <div class="button-group">
                        <el-button v-if="chatLoading && enableStreamOutput"
                                   type="warning"
                                   @click="stopRagResponse">
                          停止生成
                        </el-button>
                        <el-button type="primary" :disabled="chatLoading" @click="sendMessage">
                          发送
                        </el-button>
                      </div>
                    </div>
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
            <div class="theme-header">设置</div>
            <div class="theme-content">
              <div class="setting-section">
                <div class="setting-title">主题</div>
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
            flex-direction: column;
            border-bottom: 1px solid var(--el-border-color-light);
            margin-bottom: 8px;
            background-color: var(--el-fill-color-lighter);
            transition: all 0.3s ease;
            border-radius: 8px;
            border: 1px solid transparent;
            
            &.expanded {
              background-color: var(--el-fill-color-light);
            }

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
            
            .file-header {
              display: flex;
              align-items: center;
              justify-content: space-between;
              padding: 12px 16px;
              cursor: pointer;
              transition: background-color 0.3s;
              
              .file-actions {
                display: flex;
                align-items: center;
                gap: 12px;

                .delete-action {
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  
                  .delete-icon, .clear-icon {
                    cursor: pointer;
                    width: 16px;
                    height: 16px;
                    padding: 4px;
                    border-radius: 4px;
                    transition: all 0.3s ease;
                    opacity: 0.6;

                    &:hover {
                      opacity: 1;
                    }
                  }
                  
                  .delete-icon:hover {
                    background-color: var(--el-color-danger-light-9);
                  }
                  
                  .clear-icon:hover {
                    background-color: var(--el-color-warning-light-9);
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
            
            .file-entities-card {
              padding: 12px 16px;
              border-top: 1px dashed var(--el-border-color-light);
              background-color: var(--el-bg-color-page);
              overflow: hidden;
              transition: max-height 0.3s ease-in-out;
              
              .loading-entities {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 12px 0;
                color: var(--el-text-color-secondary);
                
                .el-icon {
                  margin-right: 8px;
                  font-size: 18px;
                }
              }
              
              .entities-error {
                padding: 8px 0;
              }
              
              .entities-title {
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 8px;
                color: var(--el-text-color-primary);
              }
              
              .entities-content {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                
                .entity-tag {
                  margin-right: 0;
                  cursor: default;
                }
              }
              
              .no-entities {
                padding: 8px 0;
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

                  .input-actions {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;

                    .button-group {
                      display: flex;
                      justify-content: flex-end;
                      gap: 10px;
                    }
                  }

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
  from {
    transform: rotate(0deg);
  }
  to {
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

  .setting-section {
    margin-bottom: 20px;

    .setting-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--el-text-color-primary);
      margin-bottom: 12px;
      border-top: 1px solid var(--el-border-color-lighter);
      padding-top: 16px;

      &:first-child {
        border-top: none;
        padding-top: 0;
      }
    }

    .setting-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      margin-bottom: 8px;
      border-radius: 6px;

      &:hover {
        background-color: var(--el-fill-color-light);
      }

      span {
        font-size: 14px;
        color: var(--el-text-color-primary);
      }
    }
  }

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

// 添加滚动按钮样式
.chat-container {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;

  .scroll-to-bottom-btn {
    position: absolute;
    bottom: 80px;
    right: 16px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: var(--el-color-primary);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    z-index: 10;
    transition: all 0.3s ease;

    &:hover {
      background-color: var(--el-color-primary-light-3);
      transform: translateY(-2px);
    }

    .el-icon {
      font-size: 20px;
    }
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    scroll-behavior: smooth;

    .message {
      display: flex;

      &.streaming {
        .message-content {
          .streaming-content {
            display: flex;
            align-items: flex-start;
            flex-direction: column;

            .answer {
              white-space: pre-wrap;
              word-break: break-word;
              width: 100%;
            }

            .cursor-blink {
              display: inline-block;
              width: 2px;
              height: 16px;
              background-color: var(--el-color-primary);
              margin-left: 2px;
              animation: cursor-blink 0.8s infinite;
            }

            .streaming-status {
              font-size: 12px;
              color: var(--el-color-info);
              margin-top: 4px;
              font-style: italic;
            }
          }
        }
      }
    }
  }
}

@keyframes cursor-blink {
  0%, 100% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}

// 自定义弹出框样式
:deep(.el-popover.custom-popover) {
  padding: 0 0 12px 0;
  border-radius: 8px;
  background-color: #fff;
  border: none;

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

.message {
  &.streaming {
    .message-content {
      .streaming-content {
        display: flex;
        align-items: flex-start;
        flex-direction: column;

        .answer {
          white-space: pre-wrap;
          word-break: break-word;
          width: 100%;
        }

        .cursor-blink {
          display: inline-block;
          width: 2px;
          height: 16px;
          background-color: var(--el-color-primary);
          margin-left: 2px;
          animation: cursor-blink 0.8s infinite;
        }
      }
    }
  }
}

@keyframes cursor-blink {
  0%, 100% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}

// 添加流式输出状态提示样式
.streaming-status {
  font-size: 12px;
  color: var(--el-color-info);
  margin-top: 4px;
  font-style: italic;
}

// 优化聊天内容区域滚动
.chat-messages {
  height: calc(100% - 100px);
  overflow-y: auto;
  scroll-behavior: smooth;
}

// 添加以下代码到样式部分的末尾：
.answer {
  white-space: pre-wrap !important;
  word-break: break-word;
  line-height: 1.6;
  width: 100%;
}
</style>
