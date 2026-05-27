<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <h1>KaoyanCrawler</h1>
      <span class="subtitle">考研数据采集系统</span>
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
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import StatsPanel from './components/StatsPanel.vue'
import SearchPanel from './components/SearchPanel.vue'
import AdmissionTable from './components/AdmissionTable.vue'

const statsPanel = ref(null)
const admissionTable = ref(null)

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
  gap: 16px;
  padding: 0 24px;
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
