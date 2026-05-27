<template>
  <el-dialog v-model="visible" title="AI智能提取" width="700px">
    <el-alert v-if="!aiAvailable" type="warning" :closable="false" style="margin-bottom: 16px">
      <template #title>
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span>AI功能未配置，请先设置API Key</span>
          <el-button type="primary" size="small" @click="openSettings">去设置</el-button>
        </div>
      </template>
    </el-alert>

    <div class="simple-form">
      <p class="form-desc">输入学校名称，AI自动搜索官网、找到名单页面、提取数据</p>
      <el-input
        v-model="university"
        placeholder="输入学校名称，如：清华大学"
        size="large"
        clearable
        @keyup.enter="startCrawl"
      >
        <template #prepend>学校名称</template>
      </el-input>

      <el-select v-model="year" style="margin-top: 12px; width: 200px">
        <el-option :value="2025" label="2025年" />
        <el-option :value="2024" label="2024年" />
        <el-option :value="2023" label="2023年" />
      </el-select>

      <el-button type="primary" @click="startCrawl" :loading="crawling" :disabled="!canStart"
                 style="width: 100%; margin-top: 20px" size="large">
        {{ crawling ? 'AI正在自动采集...' : '开始一键采集' }}
      </el-button>
    </div>

    <!-- 采集进度 -->
    <div v-if="steps.length" style="margin-top: 20px">
      <el-steps direction="vertical" :active="steps.length - 1" space="30px">
        <el-step v-for="(step, i) in steps" :key="i" :title="step" status="process" />
      </el-steps>
    </div>

    <!-- 采集结果 -->
    <div v-if="result" style="margin-top: 20px">
      <el-alert v-if="result.success" type="success" :closable="false">
        <template #title>
          采集成功！共获取 {{ totalRecords }} 条数据
        </template>
      </el-alert>

      <el-alert v-else type="error" :closable="false">
        <template #title>{{ result.errors?.[0] || '采集失败' }}</template>
      </el-alert>

      <!-- 错误信息 -->
      <div v-if="result.errors?.length" style="margin-top: 12px">
        <el-collapse>
          <el-collapse-item title="错误详情" name="errors">
            <p v-for="(err, i) in result.errors" :key="i" class="error-line">{{ err }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 数据预览 -->
      <div v-if="result.results?.length" style="margin-top: 16px">
        <h4>提取的数据：</h4>
        <div v-for="(res, i) in result.results" :key="i" style="margin-top: 12px">
          <el-card shadow="never">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>{{ res.list_type }} ({{ res.year }}年)</span>
                <el-tag type="success">{{ res.saved_count || res.count }} 条</el-tag>
              </div>
            </template>
            <p style="font-size: 13px; color: #909399">来源: {{ res.source_text }}</p>
            <el-table v-if="res.sample?.length" :data="res.sample" border size="small" style="margin-top: 8px" max-height="200">
              <el-table-column prop="name" label="姓名" width="80" />
              <el-table-column prop="major" label="专业" min-width="150" show-overflow-tooltip />
              <el-table-column prop="exam_id" label="考生编号" width="130" />
              <el-table-column prop="initial_score" label="初试" width="70" />
              <el-table-column prop="retest_score" label="复试" width="70" />
              <el-table-column prop="total_score" label="总分" width="70" />
            </el-table>
          </el-card>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['open-settings'])

const visible = ref(false)
const crawling = ref(false)
const aiAvailable = ref(false)

const university = ref('')
const year = ref(2025)
const steps = ref([])
const result = ref(null)

const canStart = computed(() => university.value.trim() && aiAvailable.value)

const openSettings = () => {
  visible.value = false
  emit('open-settings')
}

const totalRecords = computed(() => {
  if (!result.value?.results) return 0
  return result.value.results.reduce((sum, r) => sum + (r.saved_count || r.count || 0), 0)
})

const checkStatus = async () => {
  try {
    const { data } = await axios.get('/api/ai-status', { params: { t: Date.now() } })
    aiAvailable.value = data.available
  } catch (e) {
    aiAvailable.value = false
  }
}

onMounted(checkStatus)

const startCrawl = async () => {
  if (!university.value.trim()) return

  crawling.value = true
  result.value = null
  steps.value = ['开始采集...']

  try {
    const { data } = await axios.post('/api/auto-crawl', {
      university: university.value.trim(),
      year: year.value,
    })

    result.value = data
    steps.value = data.steps || []

    if (data.success) {
      ElMessage.success(`采集成功！共获取 ${totalRecords.value} 条数据`)
    } else {
      ElMessage.warning(data.errors?.[0] || '采集失败')
    }
  } catch (e) {
    result.value = { success: false, errors: [e.message] }
    ElMessage.error('采集失败: ' + e.message)
  }

  crawling.value = false
}

const open = async () => {
  visible.value = true
  result.value = null
  steps.value = []
  university.value = ''
  year.value = 2025
  await checkStatus()
}

defineExpose({ open, checkStatus })
</script>

<style scoped>
.simple-form {
  text-align: center;
  padding: 20px 40px;
}

.form-desc {
  color: #909399;
  margin-bottom: 16px;
  font-size: 14px;
}

h4 {
  color: #303133;
  margin: 0;
}

.error-line {
  color: #f56c6c;
  font-size: 13px;
  margin: 4px 0;
}
</style>
