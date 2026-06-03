<template>
  <el-dialog v-model="visible" title="图片识别 - 院校概览" :width="dialogWidth" :fullscreen="isMobile" @close="onClose">
    <!-- AI未配置提示 -->
    <el-alert v-if="!aiAvailable && recognitionMode !== '纯OCR'" type="warning" :closable="false" style="margin-bottom: 16px">
      <template #title>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span>AI模式需要配置API Key，或切换到"纯OCR"模式</span>
          <el-button type="primary" size="small" @click="$emit('open-settings')">设置</el-button>
        </div>
      </template>
    </el-alert>

    <!-- 上传区域 -->
    <div class="upload-area" v-if="!result && !loading">
      <!-- 识别模式选择 -->
      <div class="mode-select">
        <span class="mode-label">识别方式：</span>
        <el-radio-group v-model="recognitionMode" size="default">
          <el-radio-button value="AI辅助">
            <el-icon><MagicStick /></el-icon>
            AI辅助
          </el-radio-button>
          <el-radio-button value="纯OCR">
            <el-icon><Document /></el-icon>
            纯OCR
          </el-radio-button>
          <el-radio-button value="AI优先">
            <el-icon><DataAnalysis /></el-icon>
            AI优先
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 图片预览网格 -->
      <div v-if="selectedFiles.length" class="preview-grid">
        <div v-for="(file, index) in selectedFiles" :key="index" class="preview-item">
          <img :src="file.preview" :alt="file.name" />
          <div class="preview-item__name">{{ file.name }}</div>
          <button class="preview-item__remove" @click="removeFile(index)">
            <el-icon><Close /></el-icon>
          </button>
          <div v-if="file.status" class="preview-item__status" :class="'status-' + file.status">
            {{ file.statusText }}
          </div>
        </div>
      </div>

      <el-upload
        ref="uploadRef"
        class="image-uploader"
        drag
        multiple
        :auto-upload="false"
        :limit="10"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
        :before-upload="beforeUpload"
        accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
        :show-file-list="false"
      >
        <div class="upload-placeholder">
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">拖拽考研招生图片到此处，或<em>点击上传</em></div>
          <div class="upload-hint">支持同时上传多张图片（最多10张），自动合并识别结果</div>
        </div>
      </el-upload>

      <div class="action-buttons">
        <el-button
          type="primary"
          size="large"
          class="extract-btn"
          :disabled="!selectedFiles.length || (recognitionMode !== '纯OCR' && !aiAvailable)"
          @click="startExtract"
        >
          <el-icon><MagicStick /></el-icon>
          <span>开始识别 ({{ selectedFiles.length }}张图片)</span>
        </el-button>
        <el-button
          v-if="selectedFiles.length"
          size="large"
          @click="clearFiles"
        >
          <el-icon><Delete /></el-icon>
          <span>清空</span>
        </el-button>
      </div>
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

      <!-- 图片处理进度 -->
      <div v-if="selectedFiles.length > 1" class="image-progress">
        <div class="image-progress__text">
          正在处理第 {{ currentImageIndex + 1 }} / {{ selectedFiles.length }} 张图片
        </div>
        <el-progress
          :percentage="Math.round((currentImageIndex / selectedFiles.length) * 100)"
          :stroke-width="6"
          status="success"
        />
      </div>

      <div class="crawl-stats">
        <div class="crawl-stats__items">
          <div class="crawl-stats__item">
            <div class="crawl-stats__val">{{ progressPercent }}%</div>
            <div class="crawl-stats__label">当前图片进度</div>
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
          <el-tag v-if="result.imageCount > 1" type="info" size="small">
            {{ result.imageCount }} 张图片合并
          </el-tag>
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
          <el-descriptions-item label="数据年份">
            <el-select v-model="selectedYear" size="small" style="width: 100%">
              <el-option v-for="y in yearOptions" :key="y" :label="y + '年'" :value="y" />
            </el-select>
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
                <th width="30">#</th>
                <th width="100">学院</th>
                <th width="100">专业名称</th>
                <th width="70">代码</th>
                <th width="110">初试科目</th>
                <th width="60">招生</th>
                <th width="60">复试线</th>
                <th width="55">复试人</th>
                <th width="60">录取人</th>
                <th width="50">复录比</th>
                <th width="60">最低分</th>
                <th width="60">中位数</th>
                <th width="60">最高分</th>
                <th width="40">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in editableData" :key="index">
                <td class="index-cell">{{ index + 1 }}</td>
                <td>
                  <el-input v-model="row.collegeName" size="small" placeholder="学院" />
                </td>
                <td>
                  <el-input v-model="row.majorName" size="small" placeholder="专业" />
                </td>
                <td>
                  <el-input v-model="row.majorCode" size="small" placeholder="081200" />
                </td>
                <td>
                  <el-input v-model="row.subjects" size="small" placeholder="政治、英语一、数学一、408" />
                </td>
                <td>
                  <el-input v-model="row.plannedEnrollment" size="small" placeholder="30" />
                </td>
                <td>
                  <el-input v-model="row.retestScoreLine" size="small" placeholder="320" />
                </td>
                <td>
                  <el-input v-model="row.retestCount" size="small" placeholder="45" />
                </td>
                <td>
                  <el-input v-model="row.admissionCount" size="small" placeholder="30" />
                </td>
                <td>
                  <el-input v-model="row.admissionRatio" size="small" placeholder="1.5" />
                </td>
                <td>
                  <el-input v-model="row.admissionMinScore" size="small" placeholder="320" />
                </td>
                <td>
                  <el-input v-model="row.admissionMedianScore" size="small" placeholder="350" />
                </td>
                <td>
                  <el-input v-model="row.admissionMaxScore" size="small" placeholder="390" />
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

      <el-empty v-else-if="result.success" description="未识别到专业数据">
        <template #description>
          <div>未识别到专业数据</div>
          <div v-if="result.mode" style="font-size: 12px; color: var(--el-text-color-secondary); margin-top: 8px;">
            模式: {{ result.mode }} | OCR轮数: {{ result.ocr_passes || 0 }} | 学院数: {{ (result.colleges || []).length }}
          </div>
          <div v-if="result.schoolName" style="font-size: 12px; color: var(--el-color-success); margin-top: 4px;">
            学校: {{ result.schoolName }}
          </div>
          <div v-if="result.error" style="font-size: 12px; color: var(--el-color-danger); margin-top: 4px;">
            错误: {{ result.error }}
          </div>
        </template>
      </el-empty>

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
import { CircleCheckFilled, CircleCloseFilled, MoreFilled, Close, RefreshRight, MagicStick, UploadFilled, Check, Plus, Delete, DataAnalysis, Document } from '@element-plus/icons-vue'
import { useDialog } from '../composables/useDialog'

const emit = defineEmits(['open-settings', 'data-saved'])

const { isMobile, dialogWidth } = useDialog('1200px')

const visible = ref(false)
const aiAvailable = ref(false)
const loading = ref(false)
const saving = ref(false)
const selectedFiles = ref([])
const result = ref(null)
const uploadRef = ref(null)
const editableData = ref([])
const abortController = ref(null)
const currentImageIndex = ref(0)
const recognitionMode = ref('AI辅助')
const selectedYear = ref(new Date().getFullYear())
const yearOptions = Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - i)

// 进度相关
const progressPercent = ref(0)
const progressStatus = ref('')
const steps = ref([])

const STEP_NAMES = {
  init: '初始化引擎',
  ocr: 'OCR 文字提取',
  merge: '合并多轮结果',
  clean: '去除水印和噪声',
  extract: '正则表达式提取',
  structure: 'AI 数据结构化',
  finalize: '整理识别结果',
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
  selectedFiles.value = []
  result.value = null
  editableData.value = []
  loading.value = false
  progressPercent.value = 0
  progressStatus.value = ''
  steps.value = []
  currentImageIndex.value = 0
}

function onClose() {
  if (abortController.value) {
    abortController.value.abort()
  }
  resetUpload()
}

function handleFileChange(file) {
  if (file?.raw) {
    selectedFiles.value.push({
      file: file.raw,
      name: file.name,
      preview: URL.createObjectURL(file.raw),
      status: null,
      statusText: '',
    })
  }
}

function handleExceed() {
  ElMessage.warning('最多上传10张图片')
}

function removeFile(index) {
  URL.revokeObjectURL(selectedFiles.value[index].preview)
  selectedFiles.value.splice(index, 1)
}

function clearFiles() {
  selectedFiles.value.forEach(f => URL.revokeObjectURL(f.preview))
  selectedFiles.value = []
}

function beforeUpload(file) {
  const isImage = file.type.startsWith('image/')
  const isLt20M = file.size / 1024 / 1024 < 20
  if (!isImage) { ElMessage.error('只能上传图片文件'); return false }
  if (!isLt20M) { ElMessage.error('图片大小不能超过 20MB'); return false }
  return true
}

async function startExtract() {
  if (!selectedFiles.value.length) return
  if (recognitionMode.value !== '纯OCR' && !aiAvailable.value) return

  loading.value = true
  result.value = null
  editableData.value = []
  currentImageIndex.value = 0

  abortController.value = new AbortController()

  // 存储所有图片的识别结果
  const allResults = []

  for (let i = 0; i < selectedFiles.value.length; i++) {
    if (abortController.value.signal.aborted) break

    currentImageIndex.value = i
    selectedFiles.value[i].status = 'processing'
    selectedFiles.value[i].statusText = '识别中...'

    // 重置进度
    progressPercent.value = 0
    steps.value = []

    try {
      const imageResult = await extractSingleImage(selectedFiles.value[i].file)

      if (imageResult.success) {
        allResults.push(imageResult)
        selectedFiles.value[i].status = 'done'
        selectedFiles.value[i].statusText = '完成'
      } else {
        selectedFiles.value[i].status = 'error'
        selectedFiles.value[i].statusText = imageResult.error || '失败'
      }
    } catch (e) {
      selectedFiles.value[i].status = 'error'
      selectedFiles.value[i].statusText = e.message
    }
  }

  // 合并所有结果
  if (allResults.length > 0) {
    const merged = mergeResults(allResults)
    merged.imageCount = allResults.length
    console.log('[startExtract] 合并结果 keys:', Object.keys(merged))
    console.log('[startExtract] colleges 数量:', (merged.colleges || []).length)
    console.log('[startExtract] success:', merged.success)
    result.value = merged
    buildEditableData(merged)
    console.log('[startExtract] editableData 行数:', editableData.value.length)
    ElMessage.success(`识别完成，共处理 ${allResults.length} 张图片`)
  } else {
    result.value = { success: false, error: '所有图片识别失败' }
    ElMessage.error('所有图片识别失败')
  }

  loading.value = false
  abortController.value = null
}

async function extractSingleImage(file) {
  const formData = new FormData()
  formData.append('file', file)

  const resp = await fetch(`/api/extract-image?mode=${encodeURIComponent(recognitionMode.value)}`, {
    method: 'POST',
    body: formData,
    signal: abortController.value?.signal,
  })

  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventType = ''
  let finalResult = null

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
            finalResult = data
          }
          eventType = ''
        } catch (e) {
          console.warn('SSE JSON 解析失败:', line, e)
        }
      }
    }
  }

  console.log('[extractSingleImage] finalResult keys:', finalResult ? Object.keys(finalResult) : 'null')
  console.log('[extractSingleImage] success:', finalResult?.success)
  console.log('[extractSingleImage] colleges:', (finalResult?.colleges || []).length)
  return finalResult || { success: false, error: '未收到识别结果' }
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

// 合并多张图片的识别结果
function mergeResults(results) {
  if (results.length === 1) return results[0]

  const merged = {
    success: true,
    schoolName: results[0].schoolName || '',
    schoolWebsite: results[0].schoolWebsite || '',
    duration: results[0].duration || '',
    tuition: results[0].tuition || '',
    scholarship: results[0].scholarship || '',
    colleges: [],
    ocr_text: results.map(r => r.ocr_text || '').join('\n---\n'),
    cleaned_text: results.map(r => r.cleaned_text || '').join('\n---\n'),
    mode: results[0].mode || 'ocr+llm',
    ocr_passes: results.reduce((sum, r) => sum + (r.ocr_passes || 0), 0),
  }

  // 合并学院和专业
  const collegeMap = new Map()

  for (const r of results) {
    // 补充缺失的学校信息
    if (!merged.schoolName && r.schoolName) merged.schoolName = r.schoolName
    if (!merged.schoolWebsite && r.schoolWebsite) merged.schoolWebsite = r.schoolWebsite
    if (!merged.duration && r.duration) merged.duration = r.duration
    if (!merged.tuition && r.tuition) merged.tuition = r.tuition
    if (!merged.scholarship && r.scholarship) merged.scholarship = r.scholarship

    for (const college of (r.colleges || [])) {
      const key = college.collegeName || '未知学院'
      if (!collegeMap.has(key)) {
        collegeMap.set(key, {
          collegeName: college.collegeName,
          collegeWebsite: college.collegeWebsite,
          majors: [],
        })
      }
      const existingCollege = collegeMap.get(key)

      // 更新学院官网
      if (college.collegeWebsite && !existingCollege.collegeWebsite) {
        existingCollege.collegeWebsite = college.collegeWebsite
      }

      // 添加专业（去重）
      for (const major of (college.majors || [])) {
        const majorKey = major.majorName || '未知专业'
        const existingMajor = existingCollege.majors.find(m => m.majorName === majorKey)

        if (!existingMajor) {
          existingCollege.majors.push({ ...major })
        } else {
          // 合并缺失的字段
          for (const key of Object.keys(major)) {
            if (!existingMajor[key] && major[key]) {
              existingMajor[key] = major[key]
            }
          }
        }
      }
    }
  }

  merged.colleges = Array.from(collegeMap.values())
  return merged
}

// 辅助函数：从对象中取值，兼容多种字段名格式
function getField(obj, ...keys) {
  for (const key of keys) {
    if (obj[key] !== undefined && obj[key] !== null && obj[key] !== '') {
      return obj[key]
    }
  }
  return ''
}

// 将识别结果转为可编辑的扁平数据
function buildEditableData(data) {
  console.log('[buildEditableData] 输入数据 keys:', Object.keys(data))
  console.log('[buildEditableData] colleges 数量:', (data.colleges || []).length)
  if (data.colleges?.[0]?.majors?.[0]) {
    console.log('[buildEditableData] 第一个专业示例:', JSON.stringify(data.colleges[0].majors[0]))
  }
  const rows = []
  for (const college of (data.colleges || [])) {
    for (const major of (college.majors || [])) {
      // 处理 subjects 字段：可能是数组、字符串、或以逗号/顿号分隔的字符串
      let subjectsStr = ''
      if (Array.isArray(major.subjects)) {
        subjectsStr = major.subjects.filter(Boolean).join('、')
      } else if (typeof major.subjects === 'string') {
        subjectsStr = major.subjects
      } else {
        // 尝试从 subject1-4 组合
        const parts = [major.subject1, major.subject2, major.subject3, major.subject4].filter(Boolean)
        subjectsStr = parts.join('、')
      }

      rows.push({
        collegeName: getField(college, 'collegeName', 'college_name', 'department', 'dept') || '',
        collegeWebsite: getField(college, 'collegeWebsite', 'college_website') || '',
        majorName: getField(major, 'majorName', 'major_name', 'name') || '',
        majorCode: getField(major, 'majorCode', 'major_code', 'code') || '',
        subjects: subjectsStr,
        plannedEnrollment: getField(major, 'plannedEnrollment', 'planned_enrollment', 'enrollment', 'recruitCount', '招生人数') || '',
        retestScoreLine: getField(major, 'retestScoreLine', 'retest_score_line', 'scoreLine', '复试分数线') || '',
        retestCount: getField(major, 'retestCount', 'retest_count', '复试人数') || '',
        admissionCount: getField(major, 'admissionCount', 'admission_count', '录取人数') || '',
        admissionRatio: getField(major, 'admissionRatio', 'admission_ratio', '复录比') || '',
        admissionMinScore: getField(major, 'admissionMinScore', 'admission_min_score', 'minScore', '最低分') || '',
        admissionMedianScore: getField(major, 'admissionMedianScore', 'admission_median_score', 'medianScore', '中位数') || '',
        admissionMaxScore: getField(major, 'admissionMaxScore', 'admission_max_score', 'maxScore', '最高分') || '',
        admissionAvgScore: getField(major, 'admissionAvgScore', 'admission_avg_score', 'avgScore', '平均分') || '',
        transferType: getField(major, 'transferType', 'transfer_type', '调剂类型') || '',
      })
    }
  }
  console.log('[buildEditableData] 生成行数:', rows.length)
  if (rows.length > 0) {
    console.log('[buildEditableData] 第一行示例:', JSON.stringify(rows[0]))
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
    plannedEnrollment: '',
    retestScoreLine: '',
    retestCount: '',
    admissionCount: '',
    admissionRatio: '',
    admissionMinScore: '',
    admissionMedianScore: '',
    admissionMaxScore: '',
    admissionAvgScore: '',
    transferType: '',
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
      year: selectedYear.value,
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
      // 保存成功后关闭窗口
      visible.value = false
      resetUpload()
      emit('data-saved')
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

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  width: 100%;
}

.preview-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid var(--el-border-color-lighter);
  transition: border-color 0.2s;
}

.preview-item:hover {
  border-color: var(--el-color-primary);
}

.preview-item img {
  width: 100%;
  height: 100px;
  object-fit: cover;
  display: block;
}

.preview-item__name {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  padding: 4px 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-item__remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}

.preview-item:hover .preview-item__remove {
  opacity: 1;
}

.preview-item__status {
  position: absolute;
  bottom: 22px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 11px;
  padding: 2px 0;
}

.status-processing {
  background: var(--el-color-primary);
  color: white;
}

.status-done {
  background: var(--el-color-success);
  color: white;
}

.status-error {
  background: var(--el-color-danger);
  color: white;
}

/* 模式选择 */
.mode-select {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.mode-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  flex-shrink: 0;
}

.image-uploader { width: 100%; }

.image-uploader :deep(.el-upload-dragger) {
  padding: 24px;
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

.upload-icon { font-size: 40px; color: var(--el-text-color-placeholder); }

.upload-text { font-size: 14px; color: var(--el-text-color-regular); }
.upload-text em { color: var(--el-color-primary); font-style: normal; }

.upload-hint { font-size: 12px; color: var(--el-text-color-placeholder); }

.action-buttons {
  display: flex;
  gap: 12px;
}

.extract-btn { width: 220px; }

/* 进度样式 */
.progress-section { display: flex; flex-direction: column; gap: 20px; padding: 20px 0; }
.progress-header { display: flex; align-items: center; justify-content: space-between; }
.progress-title { font-size: 18px; font-weight: 600; color: var(--el-text-color-primary); margin: 0; }

.image-progress {
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  padding: 12px 16px;
}

.image-progress__text {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

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
  .preview-grid { grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); }
  .preview-item img { height: 70px; }

  .mode-select {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .mode-select .el-radio-group {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .editable-table {
    font-size: 12px;
  }

  .editable-table th,
  .editable-table td {
    padding: 6px 4px;
  }

  .table-scroll {
    margin: 0 -16px;
    padding: 0 16px;
  }
}
</style>
