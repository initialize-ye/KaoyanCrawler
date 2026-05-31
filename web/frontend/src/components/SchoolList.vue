<template>
  <div class="school-list">
    <div class="school-list__header">
      <h2 class="school-list__title">院校列表</h2>
      <el-tag type="info" size="small">{{ schools.length }} 所院校</el-tag>
    </div>

    <div v-if="loading" class="school-list__loading">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="!schools.length" class="school-list__empty">
      <el-empty description="暂无院校数据">
        <template #description>
          <div>暂无院校数据</div>
          <div style="font-size: 12px; color: var(--el-text-color-secondary); margin-top: 8px;">
            点击右上角"采集"或"图片识别"添加数据
          </div>
        </template>
      </el-empty>
    </div>

    <div v-else class="school-grid">
      <div
        v-for="school in schools"
        :key="school.name"
        class="school-card"
        :class="{ 'school-card--active': selectedSchool === school.name }"
        @click="$emit('select', school.name)"
      >
        <div class="school-card__header">
          <h3 class="school-card__name">{{ school.name }}</h3>
          <el-button
            type="danger"
            text
            size="small"
            @click.stop="$emit('delete', school.name)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>

        <div class="school-card__stats">
          <div class="stat-item" v-if="school.admission_count">
            <span class="stat-value">{{ school.admission_count }}</span>
            <span class="stat-label">录取</span>
          </div>
          <div class="stat-item" v-if="school.subject_count">
            <span class="stat-value">{{ school.subject_count }}</span>
            <span class="stat-label">科目</span>
          </div>
          <div class="stat-item" v-if="school.rule_count">
            <span class="stat-value">{{ school.rule_count }}</span>
            <span class="stat-label">规则</span>
          </div>
          <div class="stat-item" v-if="school.score_line_count">
            <span class="stat-value">{{ school.score_line_count }}</span>
            <span class="stat-label">分数线</span>
          </div>
        </div>

        <div v-if="school.website" class="school-card__website">
          <el-icon><Link /></el-icon>
          <span>{{ school.website }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Delete, Link } from '@element-plus/icons-vue'

defineProps({
  schools: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  selectedSchool: { type: String, default: null },
})

defineEmits(['select', 'delete'])
</script>

<style scoped>
.school-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.school-list__header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.school-list__title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.school-list__loading {
  padding: 20px;
}

.school-list__empty {
  padding: 40px 0;
}

.school-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.school-card {
  background: var(--el-bg-color);
  border: 2px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.school-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.school-card--active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.school-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.school-card__name {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
}

.school-card__stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--el-color-primary);
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.school-card__website {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .school-grid {
    grid-template-columns: 1fr;
  }
}
</style>
