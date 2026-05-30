<template>
  <div class="app">
    <!-- Google-style Header -->
    <header class="google-header">
      <div class="google-header__inner">
        <div class="google-header__left">
          <button class="google-header__menu" @click="toggleSidebar">
            <span class="material-icons">menu</span>
          </button>
          <div class="google-header__brand">
            <div class="google-header__logo">
              <span class="material-icons">school</span>
            </div>
            <div class="google-header__title-group">
              <h1 class="google-header__title">考研数据采集</h1>
              <span class="google-header__subtitle">KaoyanCrawler</span>
            </div>
          </div>
        </div>

        <div class="google-header__center">
          <div class="google-search">
            <span class="material-icons google-search__icon">search</span>
            <input
              v-model="searchQuery"
              type="text"
              class="google-search__input"
              placeholder="搜索学校、专业..."
              @keyup.enter="handleGlobalSearch"
            />
          </div>
        </div>

        <div class="google-header__right">
          <button class="google-header__btn" @click="imageExtractor?.open()" data-tooltip="图片识别">
            <span class="material-icons-outlined">document_scanner</span>
          </button>
          <button class="google-header__btn" @click="settingsDialog?.open()" data-tooltip="设置">
            <span class="material-icons-outlined">settings</span>
          </button>
          <button class="google-header__btn google-header__btn--primary" @click="aiExtractor?.open()">
            <span class="material-icons">auto_awesome</span>
            <span class="btn-label">开始采集</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="google-main">
      <div class="google-main__inner">
        <!-- Stats Cards Row -->
        <div class="google-stats-row">
          <StatsPanel ref="statsPanel" />
        </div>

        <!-- Content Area -->
        <div class="google-content">
          <!-- Tab Navigation -->
          <div class="google-tabs">
            <button
              v-for="tab in tabs"
              :key="tab.value"
              class="google-tab"
              :class="{ 'google-tab--active': dataMode === tab.value }"
              @click="dataMode = tab.value"
            >
              <span class="material-icons-outlined google-tab__icon">{{ tab.icon }}</span>
              <span class="google-tab__label">{{ tab.label }}</span>
            </button>
          </div>

          <!-- Search Panel -->
          <SearchPanel @search="handleSearch" v-model:mode="dataMode" />

          <!-- Table Container -->
          <div class="google-table-container">
            <AdmissionTable v-if="dataMode === 'admission'" ref="admissionTable" />
            <SubjectTable v-else-if="dataMode === 'subject'" ref="subjectTable" />
            <RetestRulesTable v-else-if="dataMode === 'rules'" ref="rulesTable" />
            <ScoreLinesTable v-else ref="scoreLinesTable" />
          </div>
        </div>
      </div>
    </main>

    <!-- Google-style Footer -->
    <footer class="google-footer">
      <div class="google-footer__inner">
        <div class="google-footer__links">
          <a href="#" class="google-footer__link">关于</a>
          <a href="#" class="google-footer__link">帮助</a>
          <a href="#" class="google-footer__link">隐私</a>
          <a href="#" class="google-footer__link">条款</a>
        </div>
        <div class="google-footer__copyright">
          <span class="material-icons" style="font-size: 14px;">school</span>
          <span>KaoyanCrawler © 2025</span>
        </div>
      </div>
    </footer>

    <!-- Dialogs -->
    <AIExtractor ref="aiExtractor" @open-settings="settingsDialog?.open()" @data-saved="refreshAll" />
    <ImageExtractor ref="imageExtractor" @open-settings="settingsDialog?.open()" />
    <SettingsDialog ref="settingsDialog" @settings-saved="aiExtractor?.checkStatus?.()" />

    <!-- Toast Notifications -->
    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, defineAsyncComponent, onMounted } from 'vue'
import StatsPanel from './components/StatsPanel.vue'
import SearchPanel from './components/SearchPanel.vue'
import AdmissionTable from './components/AdmissionTable.vue'
import SubjectTable from './components/SubjectTable.vue'
import RetestRulesTable from './components/RetestRulesTable.vue'
import ScoreLinesTable from './components/ScoreLinesTable.vue'
import ToastContainer from './components/ToastContainer.vue'
import { useToast } from './composables/useToast'

const AIExtractor = defineAsyncComponent(() => import('./components/AIExtractor.vue'))
const ImageExtractor = defineAsyncComponent(() => import('./components/ImageExtractor.vue'))
const SettingsDialog = defineAsyncComponent(() => import('./components/SettingsDialog.vue'))

const { success: showToast, info: showInfo } = useToast()

const statsPanel = ref(null)
const admissionTable = ref(null)
const subjectTable = ref(null)
const rulesTable = ref(null)
const scoreLinesTable = ref(null)
const aiExtractor = ref(null)
const imageExtractor = ref(null)
const settingsDialog = ref(null)
const dataMode = ref('admission')
const searchQuery = ref('')

const tabs = [
  { label: '录取数据', value: 'admission', icon: 'people' },
  { label: '招生目录', value: 'subject', icon: 'menu_book' },
  { label: '复试细则', value: 'rules', icon: 'description' },
  { label: '分数线', value: 'score_lines', icon: 'analytics' },
]

const toggleSidebar = () => {
  // TODO: Implement sidebar toggle
}

const handleGlobalSearch = () => {
  if (searchQuery.value.trim()) {
    handleSearch({ university: searchQuery.value.trim() })
    showInfo(`正在搜索: ${searchQuery.value.trim()}`)
  }
}

const refreshAll = () => {
  statsPanel.value?.fetchStats()
  admissionTable.value?.fetchData()
  subjectTable.value?.fetchData()
  rulesTable.value?.fetchData()
  scoreLinesTable.value?.fetchData()
}

const handleSearch = (params) => {
  if (dataMode.value === 'admission') {
    admissionTable.value?.fetchData(params)
  } else if (dataMode.value === 'subject') {
    subjectTable.value?.fetchData(params)
  } else if (dataMode.value === 'rules') {
    rulesTable.value?.fetchData(params)
  } else {
    scoreLinesTable.value?.fetchData(params)
  }
}

// 页面加载动画
onMounted(() => {
  document.body.classList.add('loaded')
})
</script>

<style>
/* ── Google Header ── */
.google-header {
  background: var(--google-surface);
  border-bottom: 1px solid var(--google-gray-200);
  position: sticky;
  top: 0;
  z-index: 1000;
  height: 64px;
}

.google-header__inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 var(--google-space-4);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--google-space-4);
}

.google-header__left {
  display: flex;
  align-items: center;
  gap: var(--google-space-4);
  flex-shrink: 0;
}

.google-header__menu {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--google-radius-full);
  border: none;
  background: transparent;
  color: var(--google-text-secondary);
  cursor: pointer;
  transition: background var(--google-transition-fast);
}

.google-header__menu:hover {
  background: var(--google-gray-100);
}

.google-header__brand {
  display: flex;
  align-items: center;
  gap: var(--google-space-3);
}

.google-header__logo {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--google-blue) 0%, var(--google-blue-dark) 100%);
  border-radius: var(--google-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.google-header__title-group {
  display: flex;
  flex-direction: column;
}

.google-header__title {
  font-family: var(--google-font);
  font-size: 18px;
  font-weight: 500;
  color: var(--google-text-primary);
  line-height: 1.2;
}

.google-header__subtitle {
  font-size: 11px;
  color: var(--google-text-tertiary);
  letter-spacing: 0.5px;
}

.google-header__center {
  flex: 1;
  max-width: 720px;
}

.google-search {
  display: flex;
  align-items: center;
  background: var(--google-gray-100);
  border-radius: var(--google-radius-full);
  padding: 0 var(--google-space-4);
  height: 44px;
  transition: all var(--google-transition-fast);
  border: 1px solid transparent;
}

.google-search:focus-within {
  background: var(--google-surface);
  border-color: var(--google-blue);
  box-shadow: 0 1px 3px rgba(66, 133, 244, 0.2);
}

.google-search__icon {
  color: var(--google-text-tertiary);
  font-size: 20px;
  margin-right: var(--google-space-3);
}

.google-search__input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--google-text-primary);
  outline: none;
}

.google-search__input::placeholder {
  color: var(--google-text-tertiary);
}

.google-header__right {
  display: flex;
  align-items: center;
  gap: var(--google-space-2);
  flex-shrink: 0;
}

.google-header__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--google-space-2);
  height: 40px;
  min-width: 40px;
  padding: 0 var(--google-space-3);
  border-radius: var(--google-radius-full);
  border: none;
  background: transparent;
  color: var(--google-text-secondary);
  cursor: pointer;
  transition: all var(--google-transition-fast);
  font-family: var(--google-font);
  font-size: 14px;
  font-weight: 500;
}

.google-header__btn:hover {
  background: var(--google-gray-100);
  color: var(--google-text-primary);
}

.google-header__btn--primary {
  background: var(--google-blue);
  color: var(--google-text-on-primary);
  padding: 0 var(--google-space-5);
}

.google-header__btn--primary:hover {
  background: var(--google-blue-dark);
  box-shadow: 0 1px 3px rgba(66, 133, 244, 0.4);
}

.btn-label {
  display: inline;
}

/* ── Google Main ── */
.google-main {
  flex: 1;
  background: var(--google-bg);
  min-height: calc(100vh - 64px - 56px);
}

.google-main__inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--google-space-6);
}

.google-stats-row {
  margin-bottom: var(--google-space-6);
}

.google-content {
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  overflow: hidden;
}

/* ── Google Tabs ── */
.google-tabs {
  display: flex;
  border-bottom: 1px solid var(--google-gray-200);
  padding: 0 var(--google-space-4);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.google-tab {
  display: flex;
  align-items: center;
  gap: var(--google-space-2);
  padding: var(--google-space-4) var(--google-space-5);
  border: none;
  background: transparent;
  color: var(--google-text-secondary);
  font-family: var(--google-font);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  position: relative;
  transition: color var(--google-transition-fast);
  white-space: nowrap;
}

.google-tab:hover {
  color: var(--google-blue);
  background: var(--google-blue-bg);
}

.google-tab--active {
  color: var(--google-blue);
}

.google-tab--active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--google-blue);
  border-radius: 3px 3px 0 0;
}

.google-tab__icon {
  font-size: 18px;
}

/* ── Google Table Container ── */
.google-table-container {
  padding: var(--google-space-4);
}

/* ── Google Footer ── */
.google-footer {
  background: var(--google-gray-50);
  border-top: 1px solid var(--google-gray-200);
  padding: var(--google-space-4) 0;
}

.google-footer__inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 var(--google-space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.google-footer__links {
  display: flex;
  gap: var(--google-space-5);
}

.google-footer__link {
  font-size: 12px;
  color: var(--google-text-secondary);
  text-decoration: none;
  transition: color var(--google-transition-fast);
}

.google-footer__link:hover {
  color: var(--google-blue);
}

.google-footer__copyright {
  display: flex;
  align-items: center;
  gap: var(--google-space-2);
  font-size: 12px;
  color: var(--google-text-tertiary);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .google-header {
    height: 56px;
  }

  .google-header__center {
    display: none;
  }

  .google-header__title-group {
    display: none;
  }

  .btn-label {
    display: none;
  }

  .google-header__btn--primary {
    padding: 0 var(--google-space-3);
    min-width: 40px;
  }

  .google-main__inner {
    padding: var(--google-space-4);
  }

  .google-tabs {
    padding: 0;
  }

  .google-tab {
    padding: var(--google-space-3) var(--google-space-4);
    flex: 1;
    justify-content: center;
  }

  .google-tab__label {
    display: none;
  }

  .google-table-container {
    padding: var(--google-space-3);
  }

  .google-footer__inner {
    flex-direction: column;
    gap: var(--google-space-3);
    text-align: center;
  }
}

/* ── Element Plus Google Style Overrides ── */
.el-button {
  font-family: var(--google-font) !important;
  border-radius: var(--google-radius-full) !important;
  font-weight: 500 !important;
}

.el-button--primary {
  background: var(--google-blue) !important;
  border-color: var(--google-blue) !important;
}

.el-button--primary:hover {
  background: var(--google-blue-dark) !important;
  border-color: var(--google-blue-dark) !important;
}

.el-input__wrapper {
  border-radius: var(--google-radius-sm) !important;
  box-shadow: none !important;
  border: 1px solid var(--google-gray-300) !important;
}

.el-input__wrapper:hover {
  border-color: var(--google-gray-400) !important;
}

.el-input__wrapper.is-focus {
  border-color: var(--google-blue) !important;
  box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2) !important;
}

.el-select .el-input__wrapper {
  border-radius: var(--google-radius-sm) !important;
}

.el-table {
  font-family: var(--google-font-roboto) !important;
  border-radius: var(--google-radius-md) !important;
  overflow: hidden;
}

.el-table th.el-table__cell {
  background: var(--google-gray-50) !important;
  color: var(--google-text-primary) !important;
  font-weight: 500 !important;
  font-size: 13px !important;
}

.el-table td.el-table__cell {
  font-size: 13px !important;
}

.el-pagination {
  font-family: var(--google-font-roboto) !important;
}

.el-pagination .el-pager li {
  border-radius: var(--google-radius-full) !important;
  min-width: 32px !important;
  height: 32px !important;
  line-height: 32px !important;
}

.el-pagination .el-pager li.is-active {
  background: var(--google-blue) !important;
  color: white !important;
}

.el-tag {
  border-radius: var(--google-radius-full) !important;
  font-family: var(--google-font) !important;
}

.el-dialog {
  border-radius: var(--google-radius-lg) !important;
  overflow: hidden;
}

.el-dialog__header {
  font-family: var(--google-font) !important;
  font-weight: 500 !important;
}

.el-message-box {
  border-radius: var(--google-radius-lg) !important;
}

/* ── Animations ── */
@keyframes google-fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.google-content {
  animation: google-fade-in 0.3s ease-out;
}

/* ── Loading States ── */
.is-loading {
  pointer-events: none;
  opacity: 0.7;
}

/* ── Page Load Animation ── */
body {
  opacity: 0;
  transition: opacity 0.3s ease-in-out;
}

body.loaded {
  opacity: 1;
}

/* ── Focus Styles ── */
*:focus-visible {
  outline: 2px solid var(--google-blue);
  outline-offset: 2px;
}

/* ── Tooltip Styles ── */
[data-tooltip] {
  position: relative;
}

[data-tooltip]::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding: 6px 12px;
  background: var(--google-gray-900);
  color: white;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--google-radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--google-transition-fast);
  z-index: 10000;
}

[data-tooltip]:hover::after {
  opacity: 1;
}
</style>
