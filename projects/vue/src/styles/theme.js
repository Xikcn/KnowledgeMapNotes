export const themes = {
  default: {
    // 默认主题不需要设置，使用 Element Plus 默认值
  },
  dark: {
    '--el-bg-color': '#1e1e1e',
    '--el-bg-color-page': '#141414',
    '--el-text-color-primary': '#ffffff',
    '--el-text-color-regular': '#e5eaf3',
    '--el-text-color-secondary': '#a8abb2',
    '--el-border-color': '#4c4d4f',
    '--el-border-color-light': '#4c4d4f',
    '--el-border-color-lighter': '#4c4d4f',
    '--el-border-color-dark': '#636466',
    '--el-fill-color-light': '#262727',
    '--el-fill-color-lighter': '#1e1e1e',
    '--el-fill-color-dark': '#262727',
    '--el-fill-color-darker': '#363637',
    '--el-color-primary': '#409eff',
    '--el-color-primary-light-3': '#3375b9',
    '--el-color-primary-light-5': '#2a598a',
    '--el-color-primary-light-7': '#213d5b',
    '--el-color-primary-light-8': '#1b2f45',
    '--el-color-primary-light-9': '#18222c',
    '--el-color-primary-dark-2': '#66b1ff',
    '--el-color-success': '#67c23a',
    '--el-color-success-light-3': '#4e8e2f',
    '--el-color-success-light-5': '#3e6b27',
    '--el-color-success-light-7': '#2d481e',
    '--el-color-success-light-8': '#243a19',
    '--el-color-success-light-9': '#1a2a13',
    '--el-color-warning': '#e6a23c',
    '--el-color-warning-light-3': '#a77730',
    '--el-color-warning-light-5': '#7d5b28',
    '--el-color-warning-light-7': '#533d1d',
    '--el-color-warning-light-8': '#3e2e17',
    '--el-color-warning-light-9': '#2a1f10',
    '--el-color-danger': '#f56c6c',
    '--el-color-danger-light-3': '#b35252',
    '--el-color-danger-light-5': '#854040',
    '--el-color-danger-light-7': '#572d2d',
    '--el-color-danger-light-8': '#412424',
    '--el-color-danger-light-9': '#2b1818',
    '--el-mask-color': 'rgba(0, 0, 0, 0.8)',
    '--el-disabled-bg-color': '#252525',
    '--el-disabled-text-color': '#666666',
    '--el-button-disabled-text-color': '#999999',
    '--el-button-disabled-bg-color': '#2a2a2a',
    '--el-button-disabled-border-color': '#444444',
    '--el-button-hover-text-color': '#409eff',
    '--el-button-hover-bg-color': '#2a2a2a',
    '--el-button-hover-border-color': '#409eff'
  },
  blue: {
    '--el-bg-color': '#f0f7ff',
    '--el-bg-color-page': '#e6f1ff',
    '--el-text-color-primary': '#303133',
    '--el-text-color-regular': '#606266',
    '--el-border-color': '#dcdfe6',
    '--el-fill-color-light': '#e6f1ff',
    '--el-fill-color-lighter': '#f0f7ff',
    '--el-fill-color-darker': '#d0e3ff'
  },
  green: {
    '--el-bg-color': '#f0f9eb',
    '--el-bg-color-page': '#e1f3d8',
    '--el-text-color-primary': '#303133',
    '--el-text-color-regular': '#606266',
    '--el-text-color-secondary': '#909399',
    '--el-border-color': '#dcdfe6',
    '--el-fill-color-light': '#e1f3d8',
    '--el-fill-color-lighter': '#f0f9eb',
    '--el-fill-color-darker': '#d1edc4',
    '--el-color-primary': '#67c23a',
    '--el-color-success': '#67c23a',
    '--el-color-warning': '#e6a23c',
    '--el-color-danger': '#f56c6c',
    '--el-color-info': '#909399',
    // RAG 问答气泡特殊配置
    '--chat-user-bubble-bg': '#d1edc4',
    '--chat-user-bubble-text': '#2c3e50',
    '--chat-assistant-bubble-bg': '#e1f3d8',
    '--chat-assistant-bubble-text': '#2c3e50'
  }
};

export const applyTheme = (theme) => {
  const root = document.documentElement;
  
  // 清除所有主题相关的样式
  Object.keys(themes).forEach(themeName => {
    root.classList.remove(`theme-${themeName}`);
  });
  
  // 重置所有变量为默认值
  if (theme !== 'default') {
    const themeVariables = themes[theme];
    Object.entries(themeVariables).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
  } else {
    // 如果是默认主题，清除所有自定义变量
    Object.keys(themes.dark).forEach(key => {
      root.style.removeProperty(key);
    });
  }
  
  // 设置当前主题的 class
  root.setAttribute('data-theme', theme);
}; 