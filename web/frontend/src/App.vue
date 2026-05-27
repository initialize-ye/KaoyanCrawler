<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <h1>KaoyanCrawler</h1>
        <span class="subtitle">考研数据采集系统</span>
      </div>
      <div class="header-right">
        <el-button type="warning" @click="settingsDialog?.open()">
          <el-icon><Setting /></el-icon>
          AI设置
        </el-button>
        <el-button type="success" @click="aiExtractor?.open()">
          <el-icon><MagicStick /></el-icon>
          AI智能提取
        </el-button>
        <el-button type="primary" @click="configWizard?.open()">
          <el-icon><Plus /></el-icon>
          添加学校配置
        </el-button>
      </div>
    </el-header>

    <el-main>
      <el-row :gutter="20">
        <el-col :span="6">
          <StatsPanel ref="statsPanel" />
        </el-col>
        <el-col :span="18">
          <SearchPanel @search="handleSearch" />
          <AdmissionTable ref="admissionTable" />
        </el-col>
      </el-row>
    </el-main>

    <ConfigWizard ref="configWizard" />
    <AIExtractor ref="aiExtractor" @open-settings="settingsDialog?.open()" />
    <SettingsDialog ref="settingsDialog" />
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import StatsPanel from './components/StatsPanel.vue'
import SearchPanel from './components/SearchPanel.vue'
import AdmissionTable from './components/AdmissionTable.vue'
import ConfigWizard from './components/ConfigWizard.vue'
import AIExtractor from './components/AIExtractor.vue'
import SettingsDialog from './components/SettingsDialog.vue'

const statsPanel = ref(null)
const admissionTable = ref(null)
const configWizard = ref(null)
const aiExtractor = ref(null)
const settingsDialog = ref(null)

const handleSearch = (params) => {
  admissionTable.value?.fetchData(params)
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.app-header h1 {
  font-size: 24px;
  font-weight: 600;
}

.app-header .subtitle {
  font-size: 14px;
  opacity: 0.8;
}

.el-main {
  padding: 24px;
}
</style>
