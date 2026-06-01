<template>
  <div class="search-panel">
    <el-form :inline="!isMobile" :model="form" @submit.prevent="onSearch" class="search-form">
      <el-form-item>
        <template #label>
          <span class="form-label">学校</span>
        </template>
        <el-input v-model="form.university" placeholder="输入学校名称" clearable class="search-input--university">
          <template #prefix>
            <span class="material-icons input-icon">school</span>
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
            <span class="material-icons input-icon">collections_bookmark</span>
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
            <span class="material-icons input-icon">business</span>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item v-if="modeProxy === 'score_lines'">
        <template #label>
          <span class="form-label">学科门类</span>
        </template>
        <el-input v-model="form.discipline" placeholder="学科门类" clearable class="search-input--major">
          <template #prefix>
            <span class="material-icons input-icon">collections_bookmark</span>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item class="search-actions">
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="onReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue'
import { useResponsive } from '../composables/useResponsive'

const { isMobile } = useResponsive()
const emit = defineEmits(['search', 'update:mode'])
const props = defineProps({ mode: { type: String, default: 'admission' } })

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
  discipline: '',
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
  if (modeProxy.value === 'score_lines' && form.discipline) {
    params.discipline = form.discipline.trim()
  }
  emit('search', params)
}

const onReset = () => {
  form.university = ''
  form.year = null
  form.major = ''
  form.list_type = ''
  form.department = ''
  form.discipline = ''
  emit('search', {})
}
</script>

<style scoped>
.search-panel {
  margin-bottom: var(--google-space-5);
  padding: var(--google-space-5);
  background: #fff;
  border-radius: var(--google-radius-md);
  border: 1px solid var(--google-gray-200);
  box-shadow: var(--google-elevation-1);
  font-family: var(--google-font-roboto);
}

.form-label {
  font-weight: 500;
  color: var(--google-text-primary);
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

.input-icon {
  font-size: 18px;
  color: var(--google-text-tertiary);
}

/* 输入框样式增强 */
.search-panel :deep(.el-input__wrapper) {
  border-radius: 8px;
  transition: all var(--google-transition-fast);
}

.search-panel :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--google-blue) inset;
}

.search-panel :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--google-blue) inset;
}

/* 按钮样式 */
.search-panel :deep(.el-button--primary) {
  background: var(--google-blue);
  border: none;
  box-shadow: 0 2px 8px rgba(66, 133, 244, 0.3);
  transition: all var(--google-transition-fast);
  font-family: var(--google-font);
}

.search-panel :deep(.el-button--primary:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(66, 133, 244, 0.4);
}

@media (max-width: 768px) {
  .search-panel {
    padding: var(--google-space-4);
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
