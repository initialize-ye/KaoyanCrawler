<template>
  <el-dialog v-model="visible" title="AI智能提取" width="700px">
    <el-alert v-if="!aiAvailable" type="warning" :closable="false" style="margin-bottom: 16px">
      <template #title>
        AI功能未启用。请设置环境变量 ANTHROPIC_API_KEY 或 DEEPSEEK_API_KEY 后重启服务。
      </template>
    </el-alert>

    <el-form :model="form" label-width="100px">
      <el-form-item label="学校名称" required>
        <el-input v-model="form.university" placeholder="如：清华大学" />
      </el-form-item>
      <el-form-item label="页面URL" required>
        <el-input v-model="form.url" placeholder="粘贴包含名单的页面URL">
          <template #append>
            <el-button @click="pasteFromClipboard">粘贴</el-button>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item label="提取类型">
        <el-radio-group v-model="form.extract_type">
          <el-radio value="admission_list">复试/录取名单</el-radio>
          <el-radio value="program_catalog">招生专业目录</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <el-button type="primary" @click="startExtract" :loading="extracting" :disabled="!canExtract"
               style="width: 100%; margin-top: 16px" size="large">
      {{ extracting ? 'AI正在分析页面...' : '开始智能提取' }}
    </el-button>

    <!-- 提取结果 -->
    <div v-if="result" style="margin-top: 20px">
      <el-alert v-if="result.success" type="success" :closable="false">
        <template #title>
          提取成功！共获取 {{ result.count }} 条{{ result.list_type || '' }}数据（{{ result.year }}年）
        </template>
      </el-alert>

      <el-alert v-else type="error" :closable="false">
        <template #title>{{ result.message || result.error || '提取失败' }}</template>
      </el-alert>

      <!-- 示例数据 -->
      <div v-if="result.sample?.length" style="margin-top: 16px">
        <h4>数据预览：</h4>
        <el-table :data="result.sample" border size="small" style="margin-top: 8px">
          <el-table-column v-for="key in Object.keys(result.sample[0])" :key="key"
                          :prop="key" :label="key" min-width="100" show-overflow-tooltip />
        </el-table>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const visible = ref(false)
const extracting = ref(false)
const aiAvailable = ref(false)

const form = ref({
  university: '',
  url: '',
  extract_type: 'admission_list',
})

const result = ref(null)

const canExtract = computed(() => {
  return form.value.university && form.value.url && aiAvailable.value
})

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/ai-status')
    aiAvailable.value = data.available
  } catch (e) {
    aiAvailable.value = false
  }
})

const pasteFromClipboard = async () => {
  try {
    const text = await navigator.clipboard.readText()
    form.value.url = text
  } catch (e) {
    ElMessage.warning('无法读取剪贴板，请手动粘贴')
  }
}

const startExtract = async () => {
  extracting.value = true
  result.value = null

  try {
    const { data } = await axios.post('/api/ai-extract', {
      university: form.value.university,
      url: form.value.url,
      extract_type: form.value.extract_type,
    })
    result.value = data

    if (data.success) {
      ElMessage.success(`成功提取 ${data.count} 条数据！`)
    }
  } catch (e) {
    result.value = { success: false, error: e.message }
    ElMessage.error('提取失败: ' + e.message)
  }

  extracting.value = false
}

const open = () => {
  visible.value = true
  result.value = null
  form.value = { university: '', url: '', extract_type: 'admission_list' }
}

defineExpose({ open })
</script>

<style scoped>
h4 {
  color: #303133;
  margin: 0;
}
</style>
