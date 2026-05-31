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

      <!-- 进度概览 -->
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

      <!-- 时间线 -->
      <div class="timeline" role="list" aria-label="识别进度">
        <div v-for="(step, i) in steps" :key="i" class="tl-item" :class="'tl-item--' + step.status" role="listitem"
          :aria-current="step.status === 'running' ? 'step' : undefined">
          <div class="tl-dot" :aria-label="step.status === 'done' ? '完成' : step.status === 'running' ? '进行中' : step.status === 'error' ? '失败' : '等待'">
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

      <!-- 预览图 -->
      <div v-if="previewUrl" class="preview-small">
        <img :src="previewUrl" alt="预览" />
      </div>
    </div>

    <!-- 识别结果 - 院校概览 -->
    <div v-if="result && !loading" class="overview-section">
      <!-- 顶部操作栏 -->
      <div class="overview-toolbar">
        <el-button type="primary" plain size="small" @click="resetUpload">
          <el-icon><RefreshRight /></el-icon>
          重新上传
        </el-button>
      </div>

      <!-- 错误信息 -->
      <el-alert v-if="result.error" type="error" :closable="false" style="margin-bottom: 16px">
        {{ result.error }}
      </el-alert>

      <!-- 院校基本信息 -->
      <div v-if="result.schoolName" class="school-header">
        <div class="school-header__main">
          <h2 class="school-name">{{ result.schoolName }}</h2>
          <a v-if="result.schoolWebsite" :href="result.schoolWebsite" target="_blank" class="school-website">
            <el-icon><Link /></el-icon>
            研究生院官网
          </a>
        </div>
        <div class="school-meta">
          <div v-if="result.duration" class="meta-item">
            <span class="meta-label">学制</span>
            <span class="meta-value">{{ result.duration }}</span>
          </div>
          <div v-if="result.tuition" class="meta-item">
            <span class="meta-label">学费</span>
            <span class="meta-value">{{ result.tuition }}</span>
          </div>
          <div v-if="result.scholarship" class="meta-item">
            <span class="meta-label">奖学金</span>
            <span class="meta-value">{{ result.scholarship }}</span>
          </div>
        </div>
      </div>

      <!-- 学院列表 -->
      <div v-if="result.colleges?.length" class="colleges-container">
        <div v-for="(college, ci) in result.colleges" :key="ci" class="college-card">
          <div class="college-header">
            <h3 class="college-name">{{ college.collegeName || `学院 ${ci + 1}` }}</h3>
            <a v-if="college.collegeWebsite" :href="college.collegeWebsite" target="_blank" class="college-website">
              <el-icon><Link /></el-icon>
              官网
            </a>
          </div>

          <!-- 专业表格 -->
          <div v-if="college.majors?.length" class="majors-table-wrapper">
            <table class="majors-table">
              <thead>
                <tr>
                  <th>专业名称</th>
                  <th>专业代码</th>
                  <th>初试科目</th>
                  <th>复试线</th>
                  <th>复试人数</th>
                  <th>招生人数</th>
                  <th>分数区间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(major, mi) in college.majors" :key="mi" @click="showMajorDetail(major)">
                  <td class="major-name-cell">
                    <span>{{ major.majorName || '-' }}</span>
                    <el-tag v-if="major.specialProgram" size="small" type="warning" class="special-tag">
                      {{ major.specialProgram }}
                    </el-tag>
                  </td>
                  <td class="code-cell">{{ major.majorCode || '-' }}</td>
                  <td class="subjects-cell">
                    <span v-if="major.subjects?.length">{{ major.subjects.join('、') }}</span>
                    <span v-else class="muted">-</span>
                  </td>
                  <td class="score-cell">{{ major.retestScoreLine || '-' }}</td>
                  <td class="count-cell">{{ major.retestCount || '-' }}</td>
                  <td class="count-cell">{{ major.plannedEnrollment || '-' }}</td>
                  <td class="range-cell">{{ major.admissionScoreRange || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <el-empty v-else description="未识别到专业信息" :image-size="60" />
        </div>
      </div>

      <!-- 专业详情弹窗 -->
      <el-dialog v-model="detailVisible" title="专业详情" width="600px" append-to-body>
        <div v-if="currentMajor" class="major-detail">
          <div class="detail-header">
            <h3>{{ currentMajor.majorName }}</h3>
            <el-tag v-if="currentMajor.majorCode" type="info">{{ currentMajor.majorCode }}</el-tag>
            <el-tag v-if="currentMajor.specialProgram" type="warning">{{ currentMajor.specialProgram }}</el-tag>
          </div>

          <el-descriptions :column="2" border size="small" class="detail-descriptions">
            <el-descriptions-item label="初试科目" :span="2">
              <span v-if="currentMajor.subjects?.length">{{ currentMajor.subjects.join('、') }}</span>
              <span v-else class="muted">未提供</span>
            </el-descriptions-item>
            <el-descriptions-item label="复试分数线">{{ currentMajor.retestScoreLine || '未提供' }}</el-descriptions-item>
            <el-descriptions-item label="复试人数">{{ currentMajor.retestCount || '未提供' }}</el-descriptions-item>
            <el-descriptions-item label="复试总分区间">{{ currentMajor.retestScoreRange || '未提供' }}</el-descriptions-item>
            <el-descriptions-item label="单科成绩区间">{{ currentMajor.singleSubjectRange || '未提供' }}</el-descriptions-item>
            <el-descriptions-item label="预计招生人数">{{ currentMajor.plannedEnrollment || '未提供' }}</el-descriptions-item>
            <el-descriptions-item label="拟录取分数区间">{{ currentMajor.admissionScoreRange || '未提供' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 复试信息 -->
          <div v-if="currentMajor.retestInfo && hasRetestInfo(currentMajor.retestInfo)" class="retest-section">
            <h4 class="retest-title">复试信息</h4>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item v-if="currentMajor.retestInfo.time" label="复试时间">
                {{ currentMajor.retestInfo.time }}
              </el-descriptions-item>
              <el-descriptions-item v-if="currentMajor.retestInfo.method" label="复试形式">
                {{ currentMajor.retestInfo.method }}
              </el-descriptions-item>
              <el-descriptions-item v-if="currentMajor.retestInfo.content" label="复试内容">
                {{ currentMajor.retestInfo.content }}
              </el-descriptions-item>
              <el-descriptions-item v-if="currentMajor.retestInfo.scoreRule" label="成绩计算">
                {{ currentMajor.retestInfo.scoreRule }}
              </el-descriptions-item>
              <el-descriptions-item v-if="currentMajor.retestInfo.remark" label="备注">
                {{ currentMajor.retestInfo.remark }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-dialog>

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
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled, MoreFilled, Close, RefreshRight, Link, MagicStick, UploadFilled } from '@element-plus/icons-vue'
import { useDialog } from '../composables/useDialog'

defineEmits(['open-settings'])

const { isMobile, dialogWidth } = useDialog('900px')

const visible = ref(false)
const aiAvailable = ref(false)
const loading = ref(false)
const selectedFile = ref(null)
const previewUrl = ref('')
const result = ref(null)
const uploadRef = ref(null)
const detailVisible = ref(false)
const currentMajor = ref(null)
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

  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  if (!isLt20M) {
    ElMessage.error('图片大小不能超过 20MB')
    return false
  }
  return true
}

async function startExtract() {
  if (!selectedFile.value || !aiAvailable.value) return

  loading.value = true
  result.value = null
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

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
    }

    // 处理 SSE 流
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
              // 进度事件
              handleProgressEvent(data)
            } else if (eventType === 'result' || data.success !== undefined) {
              // 最终结果
              result.value = data
              progressPercent.value = 100
              progressStatus.value = data.success ? 'success' : 'exception'

              if (data.success) {
                ElMessage.success('图片识别完成')
              } else {
                ElMessage.error(data.error || '识别失败')
              }
            }
            eventType = ''  // 重置事件类型
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

  // 更新总进度
  progressPercent.value = progress

  // 更新步骤列表
  const existingIndex = steps.value.findIndex(s => s.step === step)
  const stepInfo = {
    step,
    name: STEP_NAMES[step] || step,
    status,
    detail,
    progress,
  }

  if (existingIndex >= 0) {
    steps.value[existingIndex] = stepInfo
  } else {
    steps.value.push(stepInfo)
  }

  // 更新进度状态
  if (status === 'error') {
    progressStatus.value = 'exception'
  }
}

function cancelExtract() {
  if (abortController.value) {
    abortController.value.abort()
  }
}

function showMajorDetail(major) {
  currentMajor.value = major
  detailVisible.value = true
}

function hasRetestInfo(info) {
  return info.time || info.method || info.content || info.scoreRule || info.remark
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

.image-uploader {
  width: 100%;
}

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

.upload-icon {
  font-size: 48px;
  color: var(--el-text-color-placeholder);
}

.upload-text {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.upload-text em {
  color: var(--el-color-primary);
  font-style: normal;
}

.upload-hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.upload-preview {
  max-height: 400px;
  overflow: hidden;
  border-radius: 8px;
}

.upload-preview img {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
}

.extract-btn {
  width: 200px;
}

/* 进度显示样式 */
.progress-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px 0;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.progress-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
}

/* 进度概览 */
.crawl-stats {
  padding: 16px 20px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.crawl-stats__items {
  display: flex;
  justify-content: space-around;
  margin-bottom: 12px;
}

.crawl-stats__item {
  text-align: center;
}

.crawl-stats__val {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-primary);
}

.crawl-stats__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.crawl-stats__bar {
  height: 4px;
  background: var(--el-border-color-lighter);
  border-radius: 2px;
  overflow: hidden;
}

.crawl-stats__fill {
  height: 100%;
  background: linear-gradient(90deg, var(--el-color-primary), #67c23a);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* 时间线 */
.timeline {
  margin-top: 20px;
}

.tl-item {
  display: flex;
  gap: 12px;
  position: relative;
}

.tl-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  background: var(--el-bg-color);
  position: relative;
  z-index: 1;
}

.tl-item--done .tl-dot {
  border-color: #67c23a;
  color: #67c23a;
  background: #f0f9eb;
}

.tl-item--error .tl-dot {
  border-color: var(--el-color-danger);
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.tl-item--running .tl-dot {
  border-color: var(--el-color-primary);
  background: #ecf5ff;
  color: var(--el-color-primary);
}

.tl-pulse {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 2px solid var(--el-color-primary);
  animation: pulse-ring 1.5s ease-out infinite;
  opacity: 0;
}

@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 0.8; }
  100% { transform: scale(1.6); opacity: 0; }
}

.tl-spin {
  width: 12px;
  height: 12px;
  border: 2px solid var(--el-color-primary-light-5);
  border-top-color: var(--el-color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tl-line {
  position: absolute;
  left: 11px;
  top: 28px;
  width: 2px;
  bottom: 0;
  background: var(--el-border-color-lighter);
}

.tl-line--done {
  background: #67c23a;
}

.tl-item--running .tl-line {
  background: var(--el-color-primary-light-5);
}

.tl-body {
  flex: 1;
  padding-bottom: 20px;
  min-width: 0;
}

.tl-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tl-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.tl-tag {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.tl-tag--run {
  background: #ecf5ff;
  color: var(--el-color-primary);
  animation: blink 2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.tl-tag--ok {
  background: #f0f9eb;
  color: #67c23a;
}

.tl-tag--err {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.tl-detail {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.5;
}

.preview-small {
  display: flex;
  justify-content: center;
  padding: 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.preview-small img {
  max-height: 150px;
  object-fit: contain;
  border-radius: 4px;
}

/* 院校概览样式 */
.overview-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview-toolbar {
  display: flex;
  justify-content: flex-end;
}

/* 学校头部 */
.school-header {
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-8) 100%);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--el-color-primary-light-7);
}

.school-header__main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.school-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-color-primary);
  margin: 0;
}

.school-website {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--el-color-primary);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  background: var(--el-color-white);
  border-radius: 6px;
  border: 1px solid var(--el-color-primary-light-5);
  transition: all 0.2s;
}

.school-website:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.school-meta {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.meta-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

/* 学院卡片 */
.colleges-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.college-card {
  background: var(--el-fill-color-blank);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-light);
  overflow: hidden;
}

.college-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-light);
}

.college-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
}

.college-website {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--el-color-primary);
  text-decoration: none;
  font-size: 13px;
}

.college-website:hover {
  text-decoration: underline;
}

/* 专业表格 */
.majors-table-wrapper {
  overflow-x: auto;
  padding: 0 16px 16px;
}

.majors-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
}

.majors-table th,
.majors-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
}

.majors-table th {
  background: var(--el-fill-color-light);
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.majors-table tbody tr {
  cursor: pointer;
  transition: background-color 0.2s;
}

.majors-table tbody tr:hover {
  background: var(--el-color-primary-light-9);
}

.major-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.special-tag {
  flex-shrink: 0;
}

.code-cell {
  font-family: 'Consolas', 'Monaco', monospace;
  color: var(--el-text-color-secondary);
}

.subjects-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score-cell,
.count-cell,
.range-cell {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.muted {
  color: var(--el-text-color-placeholder);
}

/* 专业详情弹窗 */
.major-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.detail-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.detail-descriptions {
  margin-top: 8px;
}

.retest-section {
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px dashed var(--el-border-color);
}

.retest-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin: 0 0 12px 0;
}

/* OCR 调试文本 */
.ocr-text {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  background: var(--el-fill-color-lighter);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
}

/* 响应式 */
@media (max-width: 768px) {
  .school-header {
    padding: 16px;
  }

  .school-name {
    font-size: 20px;
  }

  .school-meta {
    gap: 16px;
  }

  .college-header {
    padding: 12px 16px;
  }

  .college-name {
    font-size: 16px;
  }

  .majors-table th,
  .majors-table td {
    padding: 8px 12px;
    font-size: 12px;
  }

  .subjects-cell {
    max-width: 120px;
  }
}
</style>
