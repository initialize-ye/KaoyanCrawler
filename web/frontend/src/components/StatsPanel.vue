<template>
  <el-card class="stats-card">
    <template #header>
      <div class="card-header">
        <el-icon><DataAnalysis /></el-icon>
        <span>数据统计</span>
      </div>
    </template>

    <div class="stat-item">
      <div class="stat-value">{{ stats.universities || 0 }}</div>
      <div class="stat-label">已采集学校</div>
    </div>

    <el-divider />

    <div class="stat-item">
      <div class="stat-value">{{ stats.admission_records || 0 }}</div>
      <div class="stat-label">录取记录</div>
    </div>

    <el-divider />

    <div class="stat-item">
      <div class="stat-value">{{ stats.exam_subjects || 0 }}</div>
      <div class="stat-label">科目记录</div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const stats = ref({})

const fetchStats = async () => {
  try {
    const { data } = await axios.get('/api/stats')
    stats.value = data
  } catch (e) {
    console.error('获取统计失败:', e)
  }
}

onMounted(fetchStats)

defineExpose({ fetchStats })
</script>

<style scoped>
.stats-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.stat-item {
  text-align: center;
  padding: 12px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}
</style>
