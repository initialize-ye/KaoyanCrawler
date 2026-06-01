<template>
  <div class="school-list">
    <div class="school-list__header">
      <h2 class="school-list__title">院校列表</h2>
      <span class="count-badge">{{ schools.length }} 所院校</span>
    </div>

    <div v-if="loading" class="school-list__loading">
      <div class="skeleton-card" v-for="i in 3" :key="i">
        <div class="skeleton-line skeleton-line--title"></div>
        <div class="skeleton-line skeleton-line--short"></div>
      </div>
    </div>

    <div v-else-if="!schools.length" class="empty-state">
      <span class="material-icons-outlined empty-state__icon">inbox</span>
      <p class="empty-state__text">暂无院校数据</p>
      <p class="empty-state__hint">点击右上角"采集"或"图片识别"添加数据</p>
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
          <div class="school-card__icon">
            <span class="material-icons">school</span>
          </div>
          <h3 class="school-card__name">{{ school.name }}</h3>
          <button
            class="card-delete-btn"
            @click.stop="$emit('delete', school.name)"
            data-tooltip="删除"
          >
            <span class="material-icons" style="font-size: 18px;">close</span>
          </button>
        </div>

        <div class="school-card__stats">
          <div class="stat-chip" v-if="school.admission_count">
            <span class="stat-chip__value">{{ school.admission_count }}</span>
            <span class="stat-chip__label">录取</span>
          </div>
          <div class="stat-chip" v-if="school.subject_count">
            <span class="stat-chip__value">{{ school.subject_count }}</span>
            <span class="stat-chip__label">科目</span>
          </div>
          <div class="stat-chip" v-if="school.rule_count">
            <span class="stat-chip__value">{{ school.rule_count }}</span>
            <span class="stat-chip__label">规则</span>
          </div>
          <div class="stat-chip" v-if="school.score_line_count">
            <span class="stat-chip__value">{{ school.score_line_count }}</span>
            <span class="stat-chip__label">分数线</span>
          </div>
        </div>

        <div v-if="school.website" class="school-card__website">
          <span class="material-icons" style="font-size: 14px;">link</span>
          <span>{{ school.website }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
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
  gap: var(--google-space-5);
}

.school-list__header {
  display: flex;
  align-items: center;
  gap: var(--google-space-3);
}

.school-list__title {
  font-family: var(--google-font);
  font-size: 22px;
  font-weight: 400;
  color: var(--google-text-primary);
  margin: 0;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  background: var(--google-gray-100);
  color: var(--google-text-secondary);
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--google-radius-full);
}

/* ── Loading Skeleton ── */
.school-list__loading {
  display: flex;
  flex-direction: column;
  gap: var(--google-space-4);
}

.skeleton-card {
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  padding: var(--google-space-5);
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, var(--google-gray-100) 25%, var(--google-gray-200) 50%, var(--google-gray-100) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--google-radius-sm);
  margin-bottom: 8px;
}

.skeleton-line--title {
  width: 60%;
  height: 18px;
}

.skeleton-line--short {
  width: 40%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Empty State ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
}

.empty-state__icon {
  font-size: 64px;
  color: var(--google-gray-300);
  margin-bottom: var(--google-space-4);
}

.empty-state__text {
  font-family: var(--google-font);
  font-size: 18px;
  color: var(--google-text-secondary);
  margin: 0 0 8px;
}

.empty-state__hint {
  font-size: 14px;
  color: var(--google-text-tertiary);
  margin: 0;
}

/* ── School Grid ── */
.school-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--google-space-4);
}

.school-card {
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  padding: var(--google-space-5);
  cursor: pointer;
  transition: all var(--google-transition-normal);
  border: 2px solid transparent;
}

.school-card:hover {
  box-shadow: var(--google-elevation-2);
  transform: translateY(-1px);
}

.school-card--active {
  border-color: var(--google-blue);
  background: var(--google-blue-bg);
}

.school-card__header {
  display: flex;
  align-items: center;
  gap: var(--google-space-3);
  margin-bottom: var(--google-space-4);
}

.school-card__icon {
  width: 36px;
  height: 36px;
  background: var(--google-blue-bg);
  border-radius: var(--google-radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--google-blue);
  font-size: 20px;
  flex-shrink: 0;
}

.school-card__name {
  flex: 1;
  font-family: var(--google-font);
  font-size: 16px;
  font-weight: 500;
  color: var(--google-text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-delete-btn {
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
  opacity: 0;
  transition: all var(--google-transition-fast);
}

.school-card:hover .card-delete-btn {
  opacity: 1;
}

.card-delete-btn:hover {
  background: #fce8e6;
  color: var(--google-red);
}

/* ── Stats ── */
.school-card__stats {
  display: flex;
  gap: var(--google-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--google-space-3);
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--google-gray-50);
  border: 1px solid var(--google-gray-200);
  border-radius: var(--google-radius-full);
}

.stat-chip__value {
  font-size: 13px;
  font-weight: 600;
  color: var(--google-blue);
  font-variant-numeric: tabular-nums;
}

.stat-chip__label {
  font-size: 11px;
  color: var(--google-text-tertiary);
}

.school-card__website {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--google-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .school-grid {
    grid-template-columns: 1fr;
  }

  .school-card__name {
    font-size: 15px;
  }
}
</style>
