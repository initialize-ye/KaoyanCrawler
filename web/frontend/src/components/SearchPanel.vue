<template>
  <el-card class="search-card">
    <el-form :inline="true" :model="form" @submit.prevent="onSearch">
      <el-form-item label="学校">
        <el-input
          v-model="form.university"
          placeholder="输入学校名称"
          clearable
          style="width: 180px"
        />
      </el-form-item>

      <el-form-item label="年份">
        <el-input-number
          v-model="form.year"
          :min="2020"
          :max="2026"
          style="width: 130px"
        />
      </el-form-item>

      <el-form-item label="专业">
        <el-input
          v-model="form.major"
          placeholder="输入专业关键词"
          clearable
          style="width: 180px"
        />
      </el-form-item>

      <el-form-item label="类型">
        <el-select v-model="form.list_type" clearable style="width: 130px">
          <el-option label="录取名单" value="录取名单" />
          <el-option label="复试名单" value="复试名单" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="onSearch">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
        <el-button @click="onReset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { reactive } from 'vue'

const emit = defineEmits(['search'])

const form = reactive({
  university: '',
  year: null,
  major: '',
  list_type: '',
})

const onSearch = () => {
  const params = {}
  if (form.university) params.university = form.university
  if (form.year) params.year = form.year
  if (form.major) params.major = form.major
  if (form.list_type) params.list_type = form.list_type
  emit('search', params)
}

const onReset = () => {
  form.university = ''
  form.year = null
  form.major = ''
  form.list_type = ''
  emit('search', {})
}
</script>

<style scoped>
.search-card {
  margin-bottom: 20px;
}
</style>
