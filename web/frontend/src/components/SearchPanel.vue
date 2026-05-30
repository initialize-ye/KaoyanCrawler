<template>
  <div class="search-panel">
    <div class="search-top">
      <el-segmented v-model="modeProxy" :options="modeOptions" size="default" />
    </div>
    <el-form :inline="!isMobile" :model="form" @submit.prevent="onSearch" class="search-form">
      <el-form-item>
        <template #label>
          <span class="form-label">学校</span>
        </template>
        <el-input v-model="form.university" placeholder="输入学校名称" clearable class="search-input--university">
          <template #prefix>
            <el-icon><School /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item>
        <template #label>
          <span class="form-label">年份</span>
        </template>
        <el-input-number v-model="form.year" :min="2020" :max="2026" controls-position="right" class="search-input--year" />
      </el-form-item>
      <el-form-item>
        <template #label>
          <span class="form-label">专业</span>
        </template>
        <el-input v-model="form.major" placeholder="专业关键词" clearable class="search-input--major">
          <template #prefix>
            <el-icon><Collection /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item v-if="modeProxy === 'admission'">
        <template #label>
          <span class="form-label">类型</span>
        </template>
        <el-select v-model="form.list_type" clearable placeholder="选择类型" class="search-input--type">
          <el-option label="录取名单" value="录取名单" />
          <el-option label="复试名单" value="复试名单" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="modeProxy === 'subject' || modeProxy === 'rules'">
        <template #label>
          <span class="form-label">学院</span>
        </template>
        <el-input v-model="form.department" placeholder="学院名称" clearable class="search-input--department">
          <template #prefix>
            <el-icon><OfficeBuilding /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item class="search-actions">
        <el-button type="primary" @click="onSearch" :icon="Search">查询</el-button>
        <el-button @click="onReset" :icon="RefreshRight">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue'
import { Search, RefreshRight, School, Collection, OfficeBuilding } from '@element-plus/icons-vue'
import { useResponsive } from '../composables/useResponsive'

const { isMobile } = useResponsive()
const emit = defineEmits(['search', 'update:mode'])
const props = defineProps({ mode: { type: String, default: 'admission' } })

const modeOptions = [
  { label: '录取数据', value: 'admission' },
  { label: '招生目录', value: 'subject' },
  { label: '复试细则', value: 'rules' },
]

const modeProxy = computed({
  get: () => props.mode,
  set: (val) => emit('update:mode', val),
})

const form = reactive({
  university: '',
  year: null,
  major: '',
  list_type: '',
  department: '',
})

const onSearch = () => {
  const params = {}
  if (form.university) params.university = form.university.trim()
  if (form.year) params.year = form.year
  if (form.major) {
    if (modeProxy.value === 'subject') params.major_name = form.major.trim()
    else params.major = form.major.trim()
  }
  if (modeProxy.value === 'admission' && form.list_type) params.list_type = form.list_type
  if ((modeProxy.value === 'subject' || modeProxy.value === 'rules') && form.department) {
    params.department = form.department.trim()
  }
  emit('search', params)
}

const onReset = () => {
  form.university = ''
  form.year = null
  form.major = ''
  form.list_type = ''
  form.department = ''
  emit('search', {})
}
</script>

<style scoped>
.search-panel {
  margin-bottom: 20px;
  padding: 20px;
  background: var(--el-bg-color);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.search-top {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
}

/* 模式切换器样式 */
.search-top :deep(.el-segmented) {
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  padding: 4px;
}

.search-top :deep(.el-segmented__item) {
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s;
}

.search-top :deep(.el-segmented__item.is-active) {
  background: linear-gradient(135deg, var(--el-color-primary) 0%, var(--el-color-primary-dark-2) 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.form-label {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.search-input--university,
.search-input--major,
.search-input--department {
  width: 200px;
}

.search-input--year {
  width: 130px;
}

.search-input--type {
  width: 140px;
}

.search-actions {
  margin-left: auto;
}

/* 输入框样式增强 */
.search-panel :deep(.el-input__wrapper) {
  border-radius: 8px;
  transition: all 0.2s;
}

.search-panel :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--el-color-primary-light-5) inset;
}

.search-panel :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}

/* 按钮样式 */
.search-panel :deep(.el-button--primary) {
  background: linear-gradient(135deg, var(--el-color-primary) 0%, var(--el-color-primary-dark-2) 100%);
  border: none;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
  transition: all 0.2s;
}

.search-panel :deep(.el-button--primary:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

@media (max-width: 768px) {
  .search-panel {
    padding: 16px;
  }

  .search-input--university,
  .search-input--major,
  .search-input--department,
  .search-input--year,
  .search-input--type {
    width: 100%;
  }

  .search-actions {
    margin-left: 0;
    width: 100%;
    display: flex;
  }

  .search-actions :deep(.el-button) {
    flex: 1;
  }
}
</style>
