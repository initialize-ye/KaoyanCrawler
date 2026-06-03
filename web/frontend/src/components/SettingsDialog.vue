<template>
  <el-dialog v-model="visible" title="设置" :width="dialogWidth" :fullscreen="isMobile">
    <el-form :model="form" label-width="80px">
      <el-form-item label="模型">
        <el-select v-model="form.ai_provider" style="width: 100%" @change="onProviderChange">
          <el-option v-for="(config, key) in providers" :key="key" :value="key" :label="config.name">
            <span>{{ config.name }}</span>
            <el-tag size="small" type="info" style="margin-left: 8px">{{ key }}</el-tag>
          </el-option>
        </el-select>
        <div class="form-hint" v-if="currentProvider">{{ currentProvider.description }}</div>
      </el-form-item>

      <el-form-item label="API Key" required>
        <el-input v-model="form.ai_api_key" type="password" show-password autocomplete="off"
          :placeholder="currentProvider?.key_placeholder || '输入API Key'" />
        <div class="form-hint">仅保存在本地</div>
      </el-form-item>

      <el-form-item label="API地址" v-if="form.ai_provider === 'custom'">
        <el-input v-model="form.ai_base_url" placeholder="https://api.example.com/chat/completions" />
      </el-form-item>

      <el-form-item label="模型名称">
        <el-select v-model="form.ai_model" filterable allow-create default-first-option
          placeholder="选择或输入模型名称" style="width: 100%">
          <el-option v-for="m in modelSuggestions" :key="m" :value="m" :label="m" />
        </el-select>
        <div class="form-hint">可直接输入自定义模型名称</div>
      </el-form-item>

      <el-divider />

      <el-form-item label="当前状态">
        <div class="status-bar">
          <el-tag v-if="aiStatus.available" type="success" effect="dark">{{ aiStatus.message }}</el-tag>
          <el-tag v-else type="danger" effect="dark">{{ aiStatus.message }}</el-tag>
          <el-button size="small" @click="testConnection" :loading="testing" style="margin-left: 12px">
            测试连接
          </el-button>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="saveSettings" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useDialog } from '../composables/useDialog'

const emit = defineEmits(['settings-saved'])
const { isMobile, dialogWidth } = useDialog('600px')

const visible = ref(false)
const saving = ref(false)
const testing = ref(false)
const providers = ref({})
const aiStatus = ref({ available: false, message: '未配置' })

const form = ref({
  ai_provider: 'deepseek',
  ai_api_key: '',
  ai_base_url: '',
  ai_model: '',
})

const currentProvider = computed(() => providers.value[form.value.ai_provider])

const MODEL_SUGGESTIONS = {
  claude: ['claude-sonnet-4-20250514', 'claude-haiku-4-20250414', 'claude-opus-4-20250514'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'o3-mini'],
  deepseek: ['deepseek-v4-flash', 'deepseek-v4-pro', 'deepseek-chat', 'deepseek-reasoner'],
  gemini: ['gemini-2.0-flash', 'gemini-2.5-pro', 'gemini-2.5-flash'],
  qwen: ['qwen-plus', 'qwen-turbo', 'qwen-max', 'qwen-long'],
  zhipu: ['glm-4-flash', 'glm-4-plus', 'glm-4-long'],
  moonshot: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
  siliconflow: ['Qwen/Qwen2.5-72B-Instruct', 'deepseek-ai/DeepSeek-V3', 'meta-llama/Llama-3.3-70B-Instruct'],
  custom: [],
}

const modelSuggestions = computed(() => {
  const list = MODEL_SUGGESTIONS[form.value.ai_provider] || []
  const cur = form.value.ai_model
  return cur && !list.includes(cur) ? [cur, ...list] : list
})

const onProviderChange = (provider) => {
  const config = providers.value[provider]
  if (config) {
    form.value.ai_base_url = config.base_url
    form.value.ai_model = config.model
  }
}

const loadProviders = async () => {
  try {
    const { data } = await axios.get('/api/ai-providers')
    providers.value = data.providers || {}
  } catch {
    ElMessage.error('加载模型列表失败')
  }
}

const loadSettings = async () => {
  try {
    const { data } = await axios.get('/api/settings')
    form.value = {
      ai_provider: data.ai_provider || 'deepseek',
      ai_api_key: data.ai_api_key || '',
      ai_base_url: data.ai_base_url || '',
      ai_model: data.ai_model || '',
    }
  } catch {
    ElMessage.error('加载设置失败')
  }
}

const loadStatus = async () => {
  try {
    const { data } = await axios.get('/api/ai-status')
    aiStatus.value = data
  } catch {
    aiStatus.value = { available: false, message: '无法获取状态' }
  }
}

const saveSettings = async () => {
  if (!form.value.ai_api_key?.trim()) {
    ElMessage.warning('请输入API Key')
    return
  }
  if (form.value.ai_provider === 'custom') {
    if (!form.value.ai_base_url?.trim()) {
      ElMessage.warning('自定义接口需要填写API地址')
      return
    }
    if (!form.value.ai_model?.trim()) {
      ElMessage.warning('自定义接口需要填写模型名称')
      return
    }
  }
  saving.value = true
  try {
    await axios.post('/api/settings', {
      ...form.value,
      ai_api_key: form.value.ai_api_key.trim(),
    })
    ElMessage.success('设置已保存')
    await loadStatus()
    emit('settings-saved')
    visible.value = false
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const testConnection = async () => {
  if (!form.value.ai_api_key?.trim()) {
    ElMessage.warning('请先输入API Key')
    return
  }
  testing.value = true
  try {
    // 先保存当前设置
    await axios.post('/api/settings', {
      ...form.value,
      ai_api_key: form.value.ai_api_key.trim(),
    })
    // 然后测试连接
    const { data } = await axios.post('/api/test-connection')
    if (data.success) {
      ElMessage.success(data.message || '连接成功')
      aiStatus.value = { available: true, message: data.message || '连接正常' }
    } else {
      ElMessage.error(data.message || '连接失败')
      aiStatus.value = { available: false, message: data.message || '连接失败' }
    }
  } catch (e) {
    ElMessage.error('测试失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

const open = async () => {
  visible.value = true
  await Promise.all([loadProviders(), loadSettings(), loadStatus()])
}

defineExpose({ open })
</script>

<style scoped>
.form-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.status-bar {
  padding: 8px 12px;
  background: var(--surface-tinted);
  border-radius: 6px;
}
</style>
