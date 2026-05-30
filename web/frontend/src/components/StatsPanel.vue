<template>
  <div class="stats-panel">
    <div class="stats-panel__header">
      <div class="stats-panel__title">数据概览</div>
      <el-button type="primary" link size="small" @click="fetchStats" :loading="loading">
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>
    <div v-if="error" class="stats-panel__error">
      <span>加载失败</span>
      <el-button type="primary" link size="small" @click="fetchStats">重试</el-button>
    </div>
    <div v-else class="stats-grid" v-loading="loading">
      <div class="stat-card stat-card--blue">
        <div class="stat-card__icon">
          <el-icon><School /></el-icon>
        </div>
        <div class="stat-card__content">
          <div class="stat-card__value">{{ stats.universities || 0 }}</div>
          <div class="stat-card__label">院校数量</div>
        </div>
      </div>
      <div class="stat-card stat-card--green">
        <div class="stat-card__icon">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-card__content">
          <div class="stat-card__value">{{ formatNumber(stats.admission_records || 0) }}</div>
          <div class="stat-card__label">录取记录</div>
        </div>
      </div>
      <div class="stat-card stat-card--orange">
        <div class="stat-card__icon">
          <el-icon><Notebook /></el-icon>
        </div>
        <div class="stat-card__content">
          <div class="stat-card__value">{{ formatNumber(stats.exam_subjects || 0) }}</div>
          <div class="stat-card__label">招生科目</div>
        </div>
      </div>
      <div class="stat-card stat-card--purple">
        <div class="stat-card__icon">
          <el-icon><DataLine /></el-icon>
        </div>
        <div class="stat-card__content">
          <div class="stat-card__value">{{ stats.score_lines || 0 }}</div>
          <div class="stat-card__label">分数线</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Refresh, School, Document, Notebook, DataLine } from '@element-plus/icons-vue'

const stats = ref({})
const loading = ref(false)
const error = ref(false)

const formatNumber = (num) => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
}

const fetchStats = async () => {
  loading.value = true
  error.value = false
  try {
    const { data } = await axios.get('/api/stats')
    stats.value = {
      universities: typeof data.universities === 'number' ? data.universities : 0,
      admission_records: typeof data.admission_records === 'number' ? data.admission_records : 0,
      exam_subjects: typeof data.exam_subjects === 'number' ? data.exam_subjects : 0,
      score_lines: typeof data.score_lines === 'number' ? data.score_lines : 0,
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
defineExpose({ fetchStats })
</script>

<style scoped>
.stats-panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  overflow: hidden;
  background: var(--el-bg-color);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.stats-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-8) 100%);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.stats-panel__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.stats-panel__error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  color: var(--el-color-danger);
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 16px;
  min-height: 120px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-card--blue {
  background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf9 100%);
}

.stat-card--blue .stat-card__icon {
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
  color: #fff;
}

.stat-card--green {
  background: linear-gradient(135deg, #e8f8e8 0%, #d1f2d1 100%);
}

.stat-card--green .stat-card__icon {
  background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%);
  color: #fff;
}

.stat-card--orange {
  background: linear-gradient(135deg, #fdf0e0 0%, #fbe4c8 100%);
}

.stat-card--orange .stat-card__icon {
  background: linear-gradient(135deg, #e6a23c 0%, #b88230 100%);
  color: #fff;
}

.stat-card--purple {
  background: linear-gradient(135deg, #f0e8fd 0%, #e4d1f9 100%);
}

.stat-card--purple .stat-card__icon {
  background: linear-gradient(135deg, #909399 0%, #73767a 100%);
  color: #fff;
}

.stat-card__icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-card__content {
  flex: 1;
  min-width: 0;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.stat-card__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 10px;
    padding: 12px;
  }

  .stat-card {
    padding: 12px;
  }

  .stat-card__icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .stat-card__value {
    font-size: 20px;
  }
}
</style>
