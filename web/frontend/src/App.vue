<template>
  <div class="app">
    <!-- Header -->
    <header class="app-header">
      <div class="app-header__inner">
        <div class="app-header__brand">
          <div class="app-header__logo">
            <el-icon><DataAnalysis /></el-icon>
          </div>
          <div class="app-header__text">
            <h1 class="app-header__title">KaoyanCrawler</h1>
            <span class="app-header__sub">考研数据采集系统</span>
          </div>
        </div>
        <div class="app-header__actions">
          <el-button :icon="Setting" @click="settingsDialog?.open()">
            <span class="btn-text">设置</span>
          </el-button>
          <el-button :icon="Picture" @click="imageExtractor?.open()">
            <span class="btn-text">图片识别</span>
          </el-button>
          <el-button :icon="MagicStick" type="primary" @click="aiExtractor?.open()">
            <span class="btn-text">开始采集</span>
          </el-button>
        </div>
      </div>
    </header>

    <!-- Body -->
    <main class="app-body">
      <div class="app-body__inner">
        <el-row :gutter="24">
          <el-col :xs="24" :sm="24" :md="8" :lg="6">
            <StatsPanel ref="statsPanel" />
          </el-col>
          <el-col :xs="24" :sm="24" :md="16" :lg="18">
            <div class="main-content">
              <SearchPanel @search="handleSearch" v-model:mode="dataMode" />
              <div class="table-container">
                <AdmissionTable v-if="dataMode === 'admission'" ref="admissionTable" />
                <SubjectTable v-else-if="dataMode === 'subject'" ref="subjectTable" />
                <RetestRulesTable v-else ref="rulesTable" />
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <div class="app-footer__inner">
        <span>KaoyanCrawler © 2025</span>
        <span class="app-footer__sep">|</span>
        <span>考研数据采集系统</span>
      </div>
    </footer>

    <!-- Dialogs -->
    <AIExtractor ref="aiExtractor" @open-settings="settingsDialog?.open()" @data-saved="refreshAll" />
    <ImageExtractor ref="imageExtractor" @open-settings="settingsDialog?.open()" />
    <SettingsDialog ref="settingsDialog" @settings-saved="aiExtractor?.checkStatus?.()" />
  </div>
</template>

<script setup>
import { ref, defineAsyncComponent } from 'vue'
import { Setting, MagicStick, Picture, DataAnalysis } from '@element-plus/icons-vue'
import StatsPanel from './components/StatsPanel.vue'
import SearchPanel from './components/SearchPanel.vue'
import AdmissionTable from './components/AdmissionTable.vue'
import SubjectTable from './components/SubjectTable.vue'
import RetestRulesTable from './components/RetestRulesTable.vue'

const AIExtractor = defineAsyncComponent(() => import('./components/AIExtractor.vue'))
const ImageExtractor = defineAsyncComponent(() => import('./components/ImageExtractor.vue'))
const SettingsDialog = defineAsyncComponent(() => import('./components/SettingsDialog.vue'))

const statsPanel = ref(null)
const admissionTable = ref(null)
const subjectTable = ref(null)
const rulesTable = ref(null)
const aiExtractor = ref(null)
const imageExtractor = ref(null)
const settingsDialog = ref(null)
const dataMode = ref('admission')

const refreshAll = () => {
  statsPanel.value?.fetchStats()
  admissionTable.value?.fetchData()
  subjectTable.value?.fetchData()
  rulesTable.value?.fetchData()
}

const handleSearch = (params) => {
  if (dataMode.value === 'admission') {
    admissionTable.value?.fetchData(params)
  } else if (dataMode.value === 'subject') {
    subjectTable.value?.fetchData(params)
  } else {
    rulesTable.value?.fetchData(params)
  }
}
</script>

<style>
/* ── Reset ── */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── App shell ── */
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── Header ── */
.app-header {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #fff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  position: sticky;
  top: 0;
  z-index: 100;
}

.app-header__inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.app-header__logo {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.app-header__text {
  display: flex;
  flex-direction: column;
}

.app-header__title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #fff 0%, #a0cfff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-header__sub {
  font-size: 11px;
  opacity: 0.7;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* header buttons */
.app-header__actions .el-button {
  --el-button-bg-color: rgba(255, 255, 255, 0.1);
  --el-button-border-color: rgba(255, 255, 255, 0.2);
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.2);
  --el-button-hover-border-color: rgba(255, 255, 255, 0.3);
  --el-button-text-color: rgba(255, 255, 255, 0.9);
  --el-button-hover-text-color: #fff;
  font-weight: 500;
  font-size: 13px;
  letter-spacing: 0.5px;
  border-radius: 8px;
  padding: 8px 16px;
  backdrop-filter: blur(10px);
  transition: all 0.2s;
}

.app-header__actions .el-button:hover {
  transform: translateY(-1px);
}

.app-header__actions .el-button--primary {
  --el-button-bg-color: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  --el-button-border-color: transparent;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%) !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.app-header__actions .el-button--primary:hover {
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.5);
}

/* ── Body ── */
.app-body {
  flex: 1;
  padding: 24px;
}

.app-body__inner {
  max-width: 1440px;
  margin: 0 auto;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.table-container {
  background: var(--el-bg-color);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  padding: 20px;
  overflow: hidden;
}

/* ── Footer ── */
.app-footer {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: rgba(255, 255, 255, 0.6);
  padding: 16px 0;
  margin-top: auto;
}

.app-footer__inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 12px;
}

.app-footer__sep {
  opacity: 0.3;
}

/* ── Card 全局样式 ── */
.el-card {
  border-color: var(--el-border-color-lighter);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.el-card__header {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  padding: 16px 20px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-8) 100%);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

/* ── Table 全局样式增强 ── */
.el-table {
  border-radius: 8px;
  overflow: hidden;
}

.el-table th.el-table__cell {
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 13px;
}

.el-table td.el-table__cell {
  font-size: 13px;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: #fafafa;
}

.el-table .el-table__row:hover > td.el-table__cell {
  background: var(--el-color-primary-light-9);
}

/* ── Pagination 全局样式 ── */
.el-pagination {
  --el-pagination-button-bg-color: var(--el-bg-color);
  --el-pagination-hover-color: var(--el-color-primary);
}

.el-pagination .el-pager li {
  border-radius: 6px;
  min-width: 32px;
  height: 32px;
  line-height: 32px;
}

.el-pagination .el-pager li.is-active {
  background: var(--el-color-primary);
  color: #fff;
  font-weight: 600;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .app-header__inner {
    padding: 0 16px;
    height: 56px;
  }

  .app-header__title {
    font-size: 15px;
  }

  .app-header__sub {
    display: none;
  }

  .app-header__logo {
    width: 36px;
    height: 36px;
    font-size: 18px;
  }

  .btn-text {
    display: none;
  }

  .app-body {
    padding: 16px;
  }

  .table-container {
    padding: 12px;
    border-radius: 8px;
  }

  .app-footer__inner {
    flex-direction: column;
    gap: 4px;
  }
}

@media (max-width: 480px) {
  .app-header__actions {
    gap: 8px;
  }

  .app-header__actions .el-button {
    padding: 6px 12px;
  }
}
</style>
