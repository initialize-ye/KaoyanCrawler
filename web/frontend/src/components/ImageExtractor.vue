<template>
  <el-dialog v-model="visible" title="图片识别 - 院校概览" :width="dialogWidth" :fullscreen="isMobile" @close="onClose">
    <!-- AI未配置提示 -->
    <el-alert v-if="!aiAvailable" type="warning" :closable="false" style="margin-bottom: 16px">
      <template #title>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span>请先配置API Key</span>
          <el-button type="primary" size="small" @click="$emit('open-settings')">设置</el-button>
        </div>
      </template>
    </el-alert>

    <!-- 上传区域 -->
    <div class="upload-area" v-if="!result && !loading">
      <el-upload
        ref="uploadRef"
        class="image-uploader"
        drag
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
        :before-upload="beforeUpload"
        accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
      >
        <div v-if="!previewUrl" class="upload-placeholder">
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">拖拽考研招生图片到此处，或<em>点击上传</em></div>
          <div class="upload-hint">支持 PNG、JPEG、GIF、WebP、BMP 格式，最大 20MB</div>
        </div>
        <div v-else class="upload-preview">
          <img :src="previewUrl" alt="预览" />
        </div>
      </el-upload>

      <el-button
        type="primary"
        size="large"
        class="extract-btn"
        :disabled="!selectedFile || !aiAvailable"
        @click="startExtract"
      >
        <el-icon><MagicStick /></el-icon>
        <span>开始识别</span>
      </el-button>
    </div>

    <!-- 进度显示 -->
    <div v-if="loading" class="progress-section">
      <div class="progress-header">
        <h3 class="progress-title">{{ currentStepName }}</h3>
        <el-button type="danger" plain size="small" @click="cancelExtract">
          <el-icon><Close /></el-icon>
          取消
        </el-button>
      </div>

      <div class="crawl-stats">
        <div class="crawl-stats__items">
          <div class="crawl-stats__item">
            <div class="crawl-stats__val">{{ progressPercent }}%</div>
            <div class="crawl-stats__label">识别进度</div>
          </div>
          <div class="crawl-stats__item">
            <div class="crawl-stats__val">{{ steps.length }}</div>
            <div class="crawl-stats__label">处理步骤</div>
          </div>
          <div class="crawl-stats__item">
            <div class="crawl-stats__val">{{ completedSteps }}</div>
            <div class="crawl-stats__label">已完成</div>
          </div>
        </div>
        <div class="crawl-stats__bar">
          <div class="crawl-stats__fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>

      <div class="timeline" role="list" aria-label="识别进度">
        <div v-for="(step, i) in steps" :key="i" class="tl-item" :class="'tl-item--' + step.status" role="listitem">
          <div class="tl-dot">
            <span v-if="step.status === 'running'" class="tl-pulse"></span>
            <span v-if="step.status === 'running'" class="tl-spin"></span>
            <el-icon v-else-if="step.status === 'done'"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="step.status === 'error'"><CircleCloseFilled /></el-icon>
            <el-icon v-else><MoreFilled /></el-icon>
          </div>
          <div v-if="i < steps.length - 1" class="tl-line" :class="{ 'tl-line--done': step.status === 'done' }"></div>
          <div class="tl-body">
            <div class="tl-head">
              <span class="tl-title">{{ step.name }}</span>
              <span v-if="step.status === 'running'" class="tl-tag tl-tag--run">进行中</span>
              <span v-else-if="step.status === 'done'" class="tl-tag tl-tag--ok">完成</span>
              <span v-else-if="step.status === 'error'" class="tl-tag tl-tag--err">失败</span>
            </div>
            <div v-if="step.detail" class="tl-detail">{{ step.detail }}</div>
          </div>
        </div>
      </div>

      <div v-if="previewUrl" class="preview-small">
        <img :src="previewUrl" alt="预览" />
      </div>
    </div>

    <!-- 识别结果 - 可编辑表格 -->
    <div v-if="result && !loading" class="result-section">
      <!-- 顶部操作栏 -->
      <div class="result-toolbar">
        <div class="result-toolbar__left">
          <el-tag :type="result.success ? 'success' : 'danger'" size="large">
            {{ result.success ? '识别成功' : '识别失败' }}
          </el-tag>
          <span v-if="result.schoolName" class="school-badge">{{ result.schoolName }}</span>
        </div>
        <div class="result-toolbar__right">
          <el-button @click="resetUpload">
            <el-icon><RefreshRight /></el-icon>
            重新上传
          </el-button>
          <el-button type="success" @click="saveToDatabase" :loading="saving" :disabled="!editableData.length">
            <el-icon><Check /></el-icon>
            确认保存 ({{ editableData.length }}条)
          </el-button>
        </div>
      </div>

      <!-- 错误信息 -->
      <el-alert v-if="result.error" type="error" :closable="false" style="margin-bottom: 16px">
        {{ result.error }}
      </el-alert>

      <!-- 学校基本信息编辑 -->
      <div v-if="result.schoolName" class="info-card">
        <h3 class="info-card__title">学校信息</h3>
        <el-descriptions :column="isMobile ? 1 : 2" border size="small">
          <el-descriptions-item label="学校名称">
            <el-input v-model="result.schoolName" size="small" />
          </el-descriptions-item>
          <el-descriptions-item label="学校官网">
            <el-input v-model="result.schoolWebsite" size="small" placeholder="https://" />
          </el-descriptions-item>
          <el-descriptions-item label="学制">
            <el-input v-model="result.duration" size="small" placeholder="如：3年" />
          </el-descriptions-item>
          <el-descriptions-item label="学费">
            <el-input v-model="result.tuition" size="small" placeholder="如：8000元/年" />
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 可编辑专业表格 -->
      <div v-if="editableData.length" class="editable-table-section">
        <div class="editable-table-header">
          <h3>识别到的专业数据（点击单元格可编辑）</h3>
          <el-button type="primary" plain size="small" @click="addRow">
            <el-icon><Plus /></el-icon>
            添加行
          </el-button>
        </div>

        <div class="table-scroll">
          <table class="editable-table">
            <thead>
              <tr>
                <th width="40">#</th>
                <th width="140">学院</th>
                <th width="140">专业名称</th>
                <th width="90">专业代码</th>
                <th width="150">初试科目</th>
                <th width="80">复试线</th>
                <th width="70">复试人数</th>
                <th width="70">招生人数</th>
                <th width="100">分数区间</th>
                <th width="60">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in editableData" :key="index">
                <td class="index-cell">{{ index + 1 }}</td>
                <td>
                  <el-input v-model="row.collegeName" size="small" placeholder="学院名称" />
                </td>
                <td>
                  <el-input v-model="row.majorName" size="small" placeholder="专业名称" />
                </td>
                <td>
                  <el-input v-model="row.majorCode" size="small" placeholder="081200" />
                </td>
                <td>
                  <el-input v-model="row.subjects" size="small" placeholder="政治、英语、数学、专业课" />
                </td>
                <td>
                  <el-input v-model="row.retestScoreLine" size="small" placeholder="320" />
                </td>
                <td>
                  <el-input v-model="row.retestCount" size="small" placeholder="45" />
                </td>
                <td>
                  <el-input v-model="row.plannedEnrollment" size="small" placeholder="30" />
                </td>
                <td>
                  <el-input v-model="row.admissionScoreRange" size="small" placeholder="320-385" />
                </td>
                <td>
                  <el-button type="danger" text size="small" @click="removeRow(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <el-empty v-else-if="result.success" description="未识别到专业数据" />

      <!-- OCR 调试信息 -->
      <el-collapse v-if="result.ocr_text" style="margin-top: 16px">
        <el-collapse-item title="OCR 清洗后文本（发送给AI）" name="cleaned">
          <pre class="ocr-text">{{ result.cleaned_text || result.ocr_text }}</pre>
        </el-collapse-item>
        <el-collapse-item title="OCR 原始文本（调试用）" name="ocr">
          <pre class="ocr-text">{{ result.ocr_text }}</pre>
        </el-collapse-item>
      </el-collapse>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled, MoreFilled, Close, RefreshRight, Link, MagicStick, UploadFilled, Check, Plus, Delete } from '@element-plus/icons-vue'
import { useDialog } from '../composables/useDialog'

defineEmits(['open-settings', 'data-saved'])

const { isMobile, dialogWidth } = useDialog('1100px')

const visible = ref(false)
const aiAvailable = ref(false)
const loading = ref(false)
const saving = ref(false)
const selectedFile = ref(null)
const previewUrl = ref('')
const result = ref(null)
const uploadRef = ref(null)
const editableData = ref([])
const abortController = ref(null)

// 进度相关
const progressPercent = ref(0)
const progressStatus = ref('')
const steps = ref([])

const STEP_NAMES = {
  init: '初始化引擎',
  ocr: 'OCR 文字提取',
  clean: '去除水印和噪声',
  structure: 'AI 数据结构化',
}

const completedSteps = computed(() => {
  return steps.value.filter(s => s.status === 'done').length
})

const currentStepName = computed(() => {
  const running = steps.value.find(s => s.status === 'running')
  if (running) return running.name + '...'
  if (steps.value.length === 0) return '准备中...'
  return '正在识别图片...'
})

function open() {
  visible.value = true
  checkStatus()
  resetUpload()
}

async function checkStatus() {
  try {
    const resp = await fetch('/api/ai-status')
    const data = await resp.json()
    aiAvailable.value = data.available
  } catch {
    aiAvailable.value = false
  }
}

function resetUpload() {
  selectedFile.value = null
  previewUrl.value = ''
  result.value = null
  editableData.value = []
  loading.value = false
  progressPercent.value = 0
  progressStatus.value = ''
  steps.value = []
  uploadRef.value?.clearFiles()
}

function onClose() {
  if (abortController.value) {
    abortController.value.abort()
  }
  resetUpload()
}

function handleFileChange(file) {
  if (file?.raw) {
    selectedFile.value = file.raw
    previewUrl.value = URL.createObjectURL(file.raw)
  }
}

function handleExceed() {
  ElMessage.warning('只能上传一张图片，请先清除已选图片')
}

function beforeUpload(file) {
  const isImage = file.type.startsWith('image/')
  const isLt20M = file.size / 1024 / 1024 < 20
  if (!isImage) { ElMessage.error('只能上传图片文件'); return false }
  if (!isLt20M) { ElMessage.error('图片大小不能超过 20MB'); return false }
  return true
}

async function startExtract() {
  if (!selectedFile.value || !aiAvailable.value) return

  loading.value = true
  result.value = null
  editableData.value = []
  progressPercent.value = 0
  progressStatus.value = ''
  steps.value = []

  abortController.value = new AbortController()

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const resp = await fetch('/api/extract-image', {
      method: 'POST',
      body: formData,
      signal: abortController.value.signal,
    })

    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let eventType = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
          continue
        }
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (eventType === 'progress' || (data.step && data.status)) {
              handleProgressEvent(data)
            } else if (eventType === 'result' || data.success !== undefined) {
              result.value = data
              progressPercent.value = 100
              progressStatus.value = data.success ? 'success' : 'exception'
              if (data.success) {
                buildEditableData(data)
                ElMessage.success('图片识别完成，请检查数据后点击保存')
              } else {
                ElMessage.error(data.error || '识别失败')
              }
            }
            eventType = ''
          } catch (e) {
            console.warn('SSE JSON 解析失败:', line, e)
          }
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      ElMessage.info('已取消识别')
    } else {
      result.value = { success: false, error: `请求失败: ${e.message}` }
      ElMessage.error(`识别失败: ${e.message}`)
    }
  } finally {
    loading.value = false
    abortController.value = null
  }
}

function handleProgressEvent(data) {
  const { step, status, detail, progress } = data
  progressPercent.value = progress

  const existingIndex = steps.value.findIndex(s => s.step === step)
  const stepInfo = { step, name: STEP_NAMES[step] || step, status, detail, progress }

  if (existingIndex >= 0) {
    steps.value[existingIndex] = stepInfo
  } else {
    steps.value.push(stepInfo)
  }

  if (status === 'error') progressStatus.value = 'exception'
}

// 将识别结果转为可编辑的扁平数据
function buildEditableData(data) {
  const rows = []
  for (const college of (data.colleges || [])) {
    for (const major of (college.majors || [])) {
      rows.push({
        collegeName: college.collegeName || '',
        collegeWebsite: college.collegeWebsite || '',
        majorName: major.majorName || '',
        majorCode: major.majorCode || '',
        subjects: (major.subjects || []).join('、'),
        retestScoreLine: major.retestScoreLine || '',
        retestCount: major.retestCount || '',
        plannedEnrollment: major.plannedEnrollment || '',
        admissionScoreRange: major.admissionScoreRange || '',
        retestScoreRange: major.retestScoreRange || '',
        singleSubjectRange: major.singleSubjectRange || '',
        specialProgram: major.specialProgram || '',
      })
    }
  }
  editableData.value = rows
}

function addRow() {
  editableData.value.push({
    collegeName: result.value?.colleges?.[0]?.collegeName || '',
    collegeWebsite: '',
    majorName: '',
    majorCode: '',
    subjects: '',
    retestScoreLine: '',
    retestCount: '',
    plannedEnrollment: '',
    admissionScoreRange: '',
    retestScoreRange: '',
    singleSubjectRange: '',
    specialProgram: '',
  })
}

function removeRow(index) {
  editableData.value.splice(index, 1)
}

function cancelExtract() {
  if (abortController.value) {
    abortController.value.abort()
  }
}

async function saveToDatabase() {
  if (!editableData.value.length) {
    ElMessage.warning('没有可保存的数据')
    return
  }

  // 过滤空行
  const validRows = editableData.value.filter(r => r.majorName.trim())
  if (!validRows.length) {
    ElMessage.warning('请至少填写一个专业名称')
    return
  }

  await ElMessageBox.confirm(
    `确定保存 ${validRows.length} 条专业数据到数据库？`,
    '确认保存',
    { type: 'info', confirmButtonText: '保存', cancelButtonText: '取消' }
  )

  saving.value = true
  try {
    const payload = {
      schoolName: result.value.schoolName || '',
      schoolWebsite: result.value.schoolWebsite || '',
      duration: result.value.duration || '',
      tuition: result.value.tuition || '',
      scholarship: result.value.scholarship || '',
      rows: validRows,
    }

    const resp = await fetch('/api/save-image-data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const data = await resp.json()
    if (data.success) {
      ElMessage.success(data.message || '保存成功')
    } else {
      ElMessage.error(data.error || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.image-uploader { width: 100%; }

.image-uploader :deep(.el-upload-dragger) {
  padding: 32px;
  border-radius: 12px;
  border: 2px dashed var(--el-border-color);
  transition: border-color 0.2s;
}

.image-uploader :deep(.el-upload-dragger:hover) {
  border-color: var(--el-color-primary);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon { font-size: 48px; color: var(--el-text-color-placeholder); }

.upload-text { font-size: 14px; color: var(--el-text-color-regular); }
.upload-text em { color: var(--el-color-primary); font-style: normal; }

.upload-hint { font-size: 12px; color: var(--el-text-color-placeholder); }

.upload-preview { max-height: 400px; overflow: hidden; border-radius: 8px; }
.upload-preview img { max-width: 100%; max-height: 400px; object-fit: contain; }

.extract-btn { width: 200px; }

/* 进度样式 */
.progress-section { display: flex; flex-direction: column; gap: 20px; padding: 20px 0; }
.progress-header { display: flex; align-items: center; justify-content: space-between; }
.progress-title { font-size: 18px; font-weight: 600; color: var(--el-text-color-primary); margin: 0; }

.crawl-stats { padding: 16px 20px; background: var(--el-fill-color-lighter); border-radius: 8px; }
.crawl-stats__items { display: flex; justify-content: space-around; margin-bottom: 12px; }
.crawl-stats__item { text-align: center; }
.crawl-stats__val { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--el-text-color-primary); }
.crawl-stats__label { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }
.crawl-stats__bar { height: 4px; background: var(--el-border-color-lighter); border-radius: 2px; overflow: hidden; }
.crawl-stats__fill { height: 100%; background: linear-gradient(90deg, var(--el-color-primary), #67c23a); border-radius: 2px; transition: width 0.3s ease; }

.timeline { margin-top: 20px; }
.tl-item { display: flex; gap: 12px; position: relative; }
.tl-dot { width: 24px; height: 24px; border-radius: 50%; border: 2px solid var(--el-border-color); display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 14px; background: var(--el-bg-color); position: relative; z-index: 1; }
.tl-item--done .tl-dot { border-color: #67c23a; color: #67c23a; background: #f0f9eb; }
.tl-item--error .tl-dot { border-color: var(--el-color-danger); color: var(--el-color-danger); background: var(--el-color-danger-light-9); }
.tl-item--running .tl-dot { border-color: var(--el-color-primary); background: #ecf5ff; color: var(--el-color-primary); }
.tl-pulse { position: absolute; inset: -5px; border-radius: 50%; border: 2px solid var(--el-color-primary); animation: pulse-ring 1.5s ease-out infinite; opacity: 0; }
@keyframes pulse-ring { 0% { transform: scale(0.8); opacity: 0.8; } 100% { transform: scale(1.6); opacity: 0; } }
.tl-spin { width: 12px; height: 12px; border: 2px solid var(--el-color-primary-light-5); border-top-color: var(--el-color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.tl-line { position: absolute; left: 11px; top: 28px; width: 2px; bottom: 0; background: var(--el-border-color-lighter); }
.tl-line--done { background: #67c23a; }
.tl-item--running .tl-line { background: var(--el-color-primary-light-5); }
.tl-body { flex: 1; padding-bottom: 20px; min-width: 0; }
.tl-head { display: flex; align-items: center; gap: 8px; }
.tl-title { font-size: 14px; font-weight: 500; color: var(--el-text-color-primary); }
.tl-tag { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.tl-tag--run { background: #ecf5ff; color: var(--el-color-primary); animation: blink 2s ease-in-out infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
.tl-tag--ok { background: #f0f9eb; color: #67c23a; }
.tl-tag--err { background: var(--el-color-danger-light-9); color: var(--el-color-danger); }
.tl-detail { font-size: 13px; color: var(--el-text-color-secondary); margin-top: 4px; line-height: 1.5; }

.preview-small { display: flex; justify-content: center; padding: 16px; background: var(--el-fill-color-lighter); border-radius: 8px; }
.preview-small img { max-height: 150px; object-fit: contain; border-radius: 4px; }

/* 结果区域 */
.result-section { display: flex; flex-direction: column; gap: 16px; }

.result-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.result-toolbar__left { display: flex; align-items: center; gap: 12px; }
.result-toolbar__right { display: flex; align-items: center; gap: 8px; }

.school-badge {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.info-card { background: var(--el-fill-color-lighter); border-radius: 8px; padding: 16px; }
.info-card__title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }

/* 可编辑表格 */
.editable-table-section { background: var(--el-fill-color-blank); border-radius: 8px; border: 1px solid var(--el-border-color-lighter); overflow: hidden; }

.editable-table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.editable-table-header h3 { font-size: 14px; font-weight: 600; margin: 0; }

.table-scroll { overflow-x: auto; padding: 12px; }

.editable-table { width: 100%; border-collapse: collapse; }

.editable-table th,
.editable-table td { padding: 8px; text-align: left; border-bottom: 1px solid var(--el-border-color-lighter); font-size: 13px; }

.editable-table th { background: var(--el-fill-color-lighter); font-weight: 600; color: var(--el-text-color-primary); white-space: nowrap; position: sticky; top: 0; }

.editable-table td .el-input { width: 100%; }

.index-cell { text-align: center; color: var(--el-text-color-secondary); font-size: 12px; }

/* OCR 文本 */
.ocr-text { font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto; background: var(--el-fill-color-lighter); padding: 12px; border-radius: 6px; border: 1px solid var(--el-border-color-lighter); }

@media (max-width: 768px) {
  .result-toolbar { flex-direction: column; align-items: flex-start; }
  .result-toolbar__right { width: 100%; }
  .result-toolbar__right .el-button { flex: 1; }
}
</style>
