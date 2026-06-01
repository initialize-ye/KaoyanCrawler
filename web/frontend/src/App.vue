<template>
  <div class="app">
    <!-- Google-style Header -->
    <header class="google-header">
      <div class="google-header__inner">
        <div class="google-header__left">
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
          <div class="google-search" :class="{ 'google-search--has-value': searchQuery }">
            <span class="material-icons google-search__icon">search</span>
            <input
              v-model="searchQuery"
              type="text"
              class="google-search__input"
              placeholder="搜索学校名称..."
              @keyup.enter="handleSearch"
            />
            <button v-if="searchQuery" class="google-search__clear" @click="searchQuery = ''">
              <span class="material-icons">close</span>
            </button>
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
        <!-- 学校列表视图 -->
        <div v-if="!selectedSchool" class="google-content">
          <SchoolList
            :schools="schoolList"
            :loading="schoolsLoading"
            :selectedSchool="selectedSchool"
            @select="selectSchool"
            @delete="deleteSchool"
          />
        </div>

        <!-- 学校详情视图 -->
        <div v-else>
          <SchoolDetail
            :schoolName="selectedSchool"
            @back="selectedSchool = null"
            @delete="deleteSchool"
            @refresh="refreshAll"
          />
        </div>
      </div>
    </main>

    <!-- Google-style Footer -->
    <footer class="google-footer">
      <div class="google-footer__inner">
        <div class="google-footer__links">
          <span class="google-footer__link">考研数据采集系统</span>
        </div>
        <div class="google-footer__copyright">
          <span class="material-icons" style="font-size: 14px;">school</span>
          <span>KaoyanCrawler © {{ new Date().getFullYear() }}</span>
        </div>
      </div>
    </footer>

    <!-- Dialogs -->
    <AIExtractor ref="aiExtractor" @open-settings="settingsDialog?.open()" @data-saved="refreshAll" />
    <ImageExtractor ref="imageExtractor" @open-settings="settingsDialog?.open()" @data-saved="refreshAll" />
    <SettingsDialog ref="settingsDialog" @settings-saved="aiExtractor?.checkStatus?.()" />

    <!-- Toast Notifications -->
    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, defineAsyncComponent, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import SchoolList from './components/SchoolList.vue'
import SchoolDetail from './components/SchoolDetail.vue'
import ToastContainer from './components/ToastContainer.vue'
import { useToast } from './composables/useToast'

const AIExtractor = defineAsyncComponent(() => import('./components/AIExtractor.vue'))
const ImageExtractor = defineAsyncComponent(() => import('./components/ImageExtractor.vue'))
const SettingsDialog = defineAsyncComponent(() => import('./components/SettingsDialog.vue'))

const { success: showToast } = useToast()

const aiExtractor = ref(null)
const imageExtractor = ref(null)
const settingsDialog = ref(null)

const searchQuery = ref('')
const selectedSchool = ref(null)
const schoolList = ref([])
const schoolsLoading = ref(false)

// 获取学校列表
const fetchSchools = async () => {
  schoolsLoading.value = true
  try {
    const { data } = await axios.get('/api/schools')
    schoolList.value = data.schools || []
  } catch (e) {
    console.error('获取学校列表失败:', e)
    schoolList.value = []
  } finally {
    schoolsLoading.value = false
  }
}

// 选择学校
const selectSchool = (schoolName) => {
  selectedSchool.value = schoolName
}

// 删除学校
const deleteSchool = async (schoolName) => {
  try {
    await ElMessageBox.confirm(
      `确定删除 "${schoolName}" 及其所有数据？此操作不可撤销。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    const { data } = await axios.delete(`/api/schools/${encodeURIComponent(schoolName)}`)
    ElMessage.success(data.message || '已删除')
    selectedSchool.value = null
    refreshAll()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

// 搜索
const handleSearch = () => {
  if (searchQuery.value.trim()) {
    selectSchool(searchQuery.value.trim())
  }
}

// 刷新所有数据
const refreshAll = () => {
  fetchSchools()
}

onMounted(() => {
  document.body.classList.add('loaded')
  fetchSchools()
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
  outline: none !important;
  box-shadow: none !important;
}

.google-search__input:focus,
.google-search__input:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

.google-search__input::placeholder {
  color: var(--google-text-tertiary);
}

.google-search__clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--google-text-tertiary);
  border-radius: var(--google-radius-full);
  cursor: pointer;
  transition: all var(--google-transition-fast);
  margin-left: var(--google-space-1);
}

.google-search__clear:hover {
  background: var(--google-gray-200);
  color: var(--google-text-primary);
}

.google-search__clear .material-icons {
  font-size: 18px;
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

.google-content {
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  padding: var(--google-space-6);
  animation: google-fade-in 0.3s ease-out;
}

/* ── Header Button Active State ── */
.google-header__btn:active {
  transform: scale(0.96);
}

.google-header__btn--primary:active {
  transform: scale(0.97);
}

/* ── Ripple Effect on Primary Button ── */
.google-header__btn--primary {
  position: relative;
  overflow: hidden;
}

.google-header__btn--primary::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(255,255,255,0.3) 0%, transparent 70%);
  opacity: 0;
  transition: opacity var(--google-transition-fast);
}

.google-header__btn--primary:active::after {
  opacity: 1;
}

/* ── Google Footer ── */
.google-footer {
  background: var(--google-gray-50);
  border-top: 1px solid var(--google-gray-200);
  padding: var(--google-space-3) 0;
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
  color: var(--google-text-tertiary);
  text-decoration: none;
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

  .google-footer__inner {
    flex-direction: column;
    gap: var(--google-space-3);
    text-align: center;
  }
}

/* ── Logo Hover ── */
.google-header__logo {
  transition: transform var(--google-transition-fast), box-shadow var(--google-transition-fast);
}

.google-header__logo:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(66, 133, 244, 0.3);
}

/* ── Custom Scrollbar ── */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--google-gray-300);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--google-gray-400);
}

/* ── Selection Color ── */
::selection {
  background: var(--google-blue-bg);
  color: var(--google-text-primary);
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
  top: calc(100% + 8px);
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
