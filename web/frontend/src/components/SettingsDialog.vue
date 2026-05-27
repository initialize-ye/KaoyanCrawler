<template>
  <el-dialog v-model="visible" title="AI设置" width="600px">
    <el-form :model="form" label-width="120px">
      <el-form-item label="AI模型">
        <el-select v-model="form.ai_provider" style="width: 100%" @change="onProviderChange">
          <el-option v-for="(config, key) in providers" :key="key" :value="key" :label="config.name">
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>{{ config.name }}</span>
              <el-tag size="small" type="info">{{ key }}</el-tag>
            </div>
          </el-option>
        </el-select>
        <div class="form-tip" v-if="currentProvider">
          {{ currentProvider.description }}
        </div>
      </el-form-item>

      <el-form-item label="API Key" required>
        <el-input v-model="form.ai_api_key" type="password" show-password
                  :placeholder="currentProvider?.key_placeholder || '输入你的API Key'" />
        <div class="form-tip">
          API Key仅保存在本地，不会上传到任何服务器
        </div>
      </el-form-item>

      <el-form-item label="API地址" v-if="form.ai_provider === 'custom'">
        <el-input v-model="form.ai_base_url" placeholder="https://api.example.com/v1/chat/completions" />
      </el-form-item>

      <el-form-item label="模型名称" v-if="form.ai_provider === 'custom'">
        <el-input v-model="form.ai_model" placeholder="gpt-4o" />
      </el-form-item>

      <el-divider />

      <el-form-item label="当前状态">
        <el-tag v-if="aiStatus.available" type="success">{{ aiStatus.message }}</el-tag>
        <el-tag v-else type="danger">{{ aiStatus.message }}</el-tag>
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

const visible = ref(false)
const saving = ref(false)

const providers = ref({})
const aiStatus = ref({ available: false, message: '未配置' })

const form = ref({
  ai_provider: 'deepseek',
  ai_api_key: '',
  ai_base_url: '',
  ai_model: '',
})

const currentProvider = computed(() => providers.value[form.value.ai_provider])

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
    providers.value = data.providers
  } catch (e) {
    console.error('加载模型列表失败:', e)
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
  } catch (e) {
    console.error('加载设置失败:', e)
  }
}

const loadStatus = async () => {
  try {
    const { data } = await axios.get('/api/ai-status')
    aiStatus.value = data
  } catch (e) {
    console.error('加载状态失败:', e)
  }
}

const saveSettings = async () => {
  if (!form.value.ai_api_key) {
    ElMessage.warning('请输入API Key')
    return
  }

  saving.value = true
  try {
    await axios.post('/api/settings', form.value)
    ElMessage.success('设置已保存')
    await loadStatus()
    visible.value = false
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  }
  saving.value = false
}

const open = async () => {
  visible.value = true
  await Promise.all([loadProviders(), loadSettings(), loadStatus()])
}

defineExpose({ open })
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
