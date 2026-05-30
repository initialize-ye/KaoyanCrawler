<template>
  <div class="google-stats-panel">
    <div class="google-stats-panel__header">
      <h2 class="google-stats-panel__title">数据概览</h2>
      <button class="google-stats-panel__refresh" @click="fetchStats" :class="{ 'is-loading': loading }">
        <span class="material-icons">refresh</span>
      </button>
    </div>

    <div v-if="error" class="google-stats-panel__error">
      <span class="material-icons">error_outline</span>
      <span>加载失败</span>
      <button class="google-btn google-btn--text" @click="fetchStats">重试</button>
    </div>

    <div v-else class="google-stats-grid">
      <div class="google-stat-card google-stat-card--blue">
        <div class="google-stat-card__icon">
          <span class="material-icons">school</span>
        </div>
        <div class="google-stat-card__content">
          <div class="google-stat-card__value">{{ stats.universities || 0 }}</div>
          <div class="google-stat-card__label">院校数量</div>
        </div>
      </div>

      <div class="google-stat-card google-stat-card--green">
        <div class="google-stat-card__icon">
          <span class="material-icons">people</span>
        </div>
        <div class="google-stat-card__content">
          <div class="google-stat-card__value">{{ formatNumber(stats.admission_records || 0) }}</div>
          <div class="google-stat-card__label">录取记录</div>
        </div>
      </div>

      <div class="google-stat-card google-stat-card--orange">
        <div class="google-stat-card__icon">
          <span class="material-icons">menu_book</span>
        </div>
        <div class="google-stat-card__content">
          <div class="google-stat-card__value">{{ formatNumber(stats.exam_subjects || 0) }}</div>
          <div class="google-stat-card__label">招生科目</div>
        </div>
      </div>

      <div class="google-stat-card google-stat-card--purple">
        <div class="google-stat-card__icon">
          <span class="material-icons">analytics</span>
        </div>
        <div class="google-stat-card__content">
          <div class="google-stat-card__value">{{ stats.score_lines || 0 }}</div>
          <div class="google-stat-card__label">分数线</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

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
.google-stats-panel {
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  overflow: hidden;
}

.google-stats-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--google-space-4) var(--google-space-5);
  border-bottom: 1px solid var(--google-gray-200);
}

.google-stats-panel__title {
  font-family: var(--google-font);
  font-size: 16px;
  font-weight: 500;
  color: var(--google-text-primary);
}

.google-stats-panel__refresh {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--google-radius-full);
  border: none;
  background: transparent;
  color: var(--google-text-secondary);
  cursor: pointer;
  transition: all var(--google-transition-fast);
}

.google-stats-panel__refresh:hover {
  background: var(--google-gray-100);
  color: var(--google-blue);
}

.google-stats-panel__refresh.is-loading .material-icons {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.google-stats-panel__error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--google-space-2);
  padding: var(--google-space-6);
  color: var(--google-red);
  font-size: 14px;
}

.google-stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--google-space-3);
  padding: var(--google-space-4);
}

.google-stat-card {
  display: flex;
  align-items: center;
  gap: var(--google-space-4);
  padding: var(--google-space-5);
  border-radius: var(--google-radius-md);
  transition: all var(--google-transition-fast);
  cursor: default;
}

.google-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--google-elevation-2);
}

.google-stat-card--blue {
  background: var(--google-blue-bg);
}

.google-stat-card--blue .google-stat-card__icon {
  background: var(--google-blue);
  color: white;
}

.google-stat-card--green {
  background: var(--google-green-bg);
}

.google-stat-card--green .google-stat-card__icon {
  background: var(--google-green);
  color: white;
}

.google-stat-card--orange {
  background: #FEF7E0;
}

.google-stat-card--orange .google-stat-card__icon {
  background: var(--google-yellow);
  color: white;
}

.google-stat-card--purple {
  background: #F3E8FD;
}

.google-stat-card--purple .google-stat-card__icon {
  background: #9334E6;
  color: white;
}

.google-stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--google-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.google-stat-card__content {
  flex: 1;
  min-width: 0;
}

.google-stat-card__value {
  font-family: var(--google-font);
  font-size: 28px;
  font-weight: 500;
  color: var(--google-text-primary);
  line-height: 1.2;
}

.google-stat-card__label {
  font-size: 13px;
  color: var(--google-text-secondary);
  margin-top: var(--google-space-1);
}

@media (max-width: 768px) {
  .google-stats-grid {
    grid-template-columns: 1fr;
    gap: var(--google-space-2);
    padding: var(--google-space-3);
  }

  .google-stat-card {
    padding: var(--google-space-4);
  }

  .google-stat-card__icon {
    width: 44px;
    height: 44px;
    font-size: 22px;
  }

  .google-stat-card__value {
    font-size: 24px;
  }
}
</style>
