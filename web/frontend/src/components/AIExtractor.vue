<template>
  <el-dialog v-model="visible" title="数据采集" :width="dialogWidth" :fullscreen="isMobile" @close="onDialogClose">
    <ConfettiEffect ref="confetti" />
    <!-- AI未配置提示 -->
    <el-alert v-if="!aiAvailable" type="warning" :closable="false" style="margin-bottom: 16px">
      <template #title>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span>请先配置API Key</span>
          <el-button type="primary" size="small" @click="openSettings">设置</el-button>
        </div>
      </template>
    </el-alert>

    <!-- 功能切换 -->
    <div class="crawl-tabs">
      <el-segmented v-model="crawlMode" :options="crawlModeOptions" size="default" />
    </div>

    <!-- 采集模式 -->
    <div class="crawl-mode">
      <el-radio-group v-model="extractType" :disabled="crawling || manualLoading" size="large">
        <el-radio-button v-for="opt in currentExtractOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 自动采集输入 -->
    <div v-if="crawlMode === 'auto'" class="crawl-input">
      <div class="crawl-input__row">
        <el-input v-model="university" placeholder="学校名称" size="large" clearable
          @keyup.enter="startCrawl" :disabled="crawling" class="crawl-input__uni">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="year" size="large" :disabled="crawling" class="crawl-input__year">
          <el-option :value="2026" label="2026" />
          <el-option :value="2025" label="2025" />
          <el-option :value="2024" label="2024" />
          <el-option :value="2023" label="2023" />
        </el-select>
      </div>
      <el-select v-model="majors" multiple filterable allow-create default-first-option
        placeholder="专业（可选，可多选）" size="large" clearable
        :disabled="crawling" class="crawl-input__majors">
        <el-option v-for="m in commonMajors" :key="m" :label="m" :value="m" />
      </el-select>
      <el-button v-if="!crawling" type="primary" size="large" class="crawl-input__btn"
        :disabled="!canStart" @click="startCrawl">
        <el-icon><VideoPlay /></el-icon>
        <span>开始采集</span>
      </el-button>
      <el-button v-else type="danger" size="large" class="crawl-input__btn" @click="cancelCrawl">
        <el-icon><VideoPause /></el-icon>
        <span>停止采集</span>
      </el-button>
    </div>

    <!-- 指定网址输入 -->
    <div v-else class="crawl-input">
      <el-input v-model="manualUrl" placeholder="网页URL" size="large" clearable
        @keyup.enter="startManual" :disabled="manualLoading">
        <template #prefix><el-icon><Link /></el-icon></template>
      </el-input>
      <el-input v-model="manualUniversity" placeholder="学校名称（可选）" size="large" clearable
        :disabled="manualLoading" />
      <el-button type="primary" size="large" class="crawl-input__btn"
        :disabled="!manualUrl.trim() || !aiAvailable || manualLoading" :loading="manualLoading"
        @click="startManual">
        <el-icon><MagicStick /></el-icon>
        <span>{{ manualLoading ? '提取中...' : '提取' }}</span>
      </el-button>
    </div>

    <!-- 进度概览 -->
    <div v-if="steps.length" class="crawl-stats">
      <div class="crawl-stats__items">
        <div class="crawl-stats__item">
          <div class="crawl-stats__val">{{ pageCount }}</div>
          <div class="crawl-stats__label">已访问页面</div>
        </div>
        <div class="crawl-stats__item">
          <div class="crawl-stats__val">{{ foundCount }}</div>
          <div class="crawl-stats__label">发现名单</div>
        </div>
        <div class="crawl-stats__item">
          <div class="crawl-stats__val">{{ elapsedTime }}</div>
          <div class="crawl-stats__label">耗时</div>
        </div>
      </div>
      <div class="crawl-stats__bar">
        <div class="crawl-stats__fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
    </div>

    <!-- 时间线 -->
    <div v-if="steps.length" class="timeline" role="list" aria-label="采集进度">
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
            <span class="tl-title">{{ step.step }}</span>
            <span v-if="step.status === 'running'" class="tl-tag tl-tag--run">进行中</span>
            <span v-else-if="step.status === 'done'" class="tl-tag tl-tag--ok">完成</span>
            <span v-else-if="step.status === 'error'" class="tl-tag tl-tag--err">失败</span>
          </div>
          <div v-if="step.detail" class="tl-detail">{{ step.detail }}</div>
        </div>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="finalResult" class="crawl-result">
      <div v-if="finalResult.success" class="crawl-result__banner crawl-result__banner--ok">
        <div class="crawl-result__icon"><el-icon :size="28"><CircleCheckFilled /></el-icon></div>
        <div>
          <div class="crawl-result__title">{{ successTitle }}</div>
          <div class="crawl-result__desc">共获取 <strong>{{ totalRecords }}</strong> 条{{ successDataType }}数据{{ successSuffix }}</div>
        </div>
      </div>
      <div v-else class="crawl-result__banner crawl-result__banner--fail">
        <div class="crawl-result__icon"><el-icon :size="28"><CircleCloseFilled /></el-icon></div>
        <div>
          <div class="crawl-result__title">采集未成功</div>
          <div class="crawl-result__desc">{{ errorMessage }}</div>
        </div>
      </div>

      <el-collapse v-if="finalResult.errors?.length" style="margin-top: 12px">
        <el-collapse-item title="错误详情" name="1">
          <p v-for="(err, j) in finalResult.errors" :key="j" class="crawl-result__err">{{ err }}</p>
        </el-collapse-item>
      </el-collapse>

      <div v-if="finalResult.results?.length" class="crawl-result__cards">
        <div v-for="(res, j) in finalResult.results" :key="j" class="res-card">
          <div class="res-card__head">
            <span class="res-card__title">{{ res.list_type }} ({{ res.year }}年)</span>
            <span class="res-card__count">{{ res.saved_count || res.count }} 条</span>
          </div>
          <div class="res-card__src">来源: {{ res.source_text }}</div>
          <el-table v-if="res.sample?.length" :data="res.sample" border size="small" max-height="200"
            style="margin-top: 8px">
            <el-table-column prop="name" label="姓名" width="80" />
            <el-table-column prop="major" label="专业" min-width="150" show-overflow-tooltip />
            <el-table-column prop="exam_id" label="考生编号" width="130" />
            <el-table-column prop="initial_score" label="初试" width="70" />
            <el-table-column prop="retest_score" label="复试" width="70" />
            <el-table-column prop="total_score" label="总分" width="70" />
          </el-table>
        </div>
      </div>
    </div>

    <!-- 人工采集结果 -->
    <div v-if="manualResult" class="crawl-result">
      <div v-if="manualResult.success" class="crawl-result__banner crawl-result__banner--ok crawl-result__banner--celebrate">
        <div class="crawl-result__icon"><el-icon :size="28"><CircleCheckFilled /></el-icon></div>
        <div>
          <div class="crawl-result__title">{{ manualResult.count >= 50 ? '收获满满！' : '提取成功' }}</div>
          <div class="crawl-result__desc">
            {{ manualResult.university }} · 共 <strong>{{ manualResult.count }}</strong> 条{{ manualResult.list_type === '复试分数线' ? '分数线' : '数据' }}
          </div>
        </div>
      </div>
      <div v-else-if="manualResult.is_dynamic" class="crawl-result__banner crawl-result__banner--warn">
        <div class="crawl-result__icon"><el-icon :size="28"><WarningFilled /></el-icon></div>
        <div>
          <div class="crawl-result__title">动态查询系统</div>
          <div class="crawl-result__desc">{{ manualResult.message }}</div>
        </div>
      </div>
      <div v-else class="crawl-result__banner crawl-result__banner--fail">
        <div class="crawl-result__icon"><el-icon :size="28"><CircleCloseFilled /></el-icon></div>
        <div>
          <div class="crawl-result__title">提取失败</div>
          <div class="crawl-result__desc">{{ manualResult.message || manualResult.error }}</div>
        </div>
      </div>

      <!-- 动态系统提示 -->
      <div v-if="manualResult.is_dynamic" class="dynamic-tip">
        <p v-if="manualResult.suggestion">{{ manualResult.suggestion }}</p>
        <p v-if="manualResult.data_url">
          数据页面: <a :href="manualResult.data_url" target="_blank" rel="noopener">{{ manualResult.data_url }}</a>
        </p>
        <div v-if="manualResult.options?.length" class="dynamic-tip__options">
          <p>页面中发现以下专业选项（需在浏览器中手动查询）：</p>
          <div class="dynamic-tip__list">
            <el-tag v-for="opt in manualResult.options.slice(0, 10)" :key="opt.value" size="small" class="dynamic-tip__tag">
              {{ opt.text }}
            </el-tag>
            <span v-if="manualResult.options.length > 10" class="dynamic-tip__more">
              ...共 {{ manualResult.options.length }} 个选项
            </span>
          </div>
        </div>
      </div>

      <!-- 名单类结果 -->
      <el-table v-if="manualResult.sample?.length && extractType !== 'retest_rules' && extractType !== 'program_catalog'"
        :data="manualResult.sample" border size="small" max-height="250" style="margin-top: 12px">
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column prop="major" label="专业" min-width="150" show-overflow-tooltip />
        <el-table-column prop="exam_id" label="考生编号" width="130" />
        <el-table-column prop="initial_score" label="初试" width="70" />
        <el-table-column prop="retest_score" label="复试" width="70" />
        <el-table-column prop="total_score" label="总分" width="70" />
      </el-table>

      <!-- 招生目录结果 -->
      <el-table v-if="manualResult.sample?.length && extractType === 'program_catalog'"
        :data="manualResult.sample" border size="small" max-height="250" style="margin-top: 12px">
        <el-table-column prop="department" label="学院" min-width="120" show-overflow-tooltip />
        <el-table-column prop="major_code" label="专业代码" width="100" />
        <el-table-column prop="major_name" label="专业名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="subject3" label="业务课一" min-width="130" show-overflow-tooltip />
        <el-table-column prop="subject4" label="业务课二" min-width="130" show-overflow-tooltip />
      </el-table>

      <!-- 复试细则结果 -->
      <div v-if="extractType === 'retest_rules' && manualResult.sample?.length" class="rules-result">
        <div v-for="(rule, i) in manualResult.sample" :key="i" class="rule-card">
          <h4 class="rule-card__title">{{ rule.title }}</h4>
          <div class="rule-card__info">
            <span>{{ rule.university }}</span>
            <span v-if="rule.department"> · {{ rule.department }}</span>
            <span v-if="rule.major"> · {{ rule.major }}</span>
            <span> · {{ rule.year }}年</span>
          </div>
          <div class="rule-card__section" v-if="rule.content_summary">
            <div class="rule-card__label">内容摘要</div>
            <div class="rule-card__text">{{ rule.content_summary }}</div>
          </div>
          <div class="rule-card__section" v-if="rule.retest_format">
            <div class="rule-card__label">复试形式</div>
            <div class="rule-card__text">{{ rule.retest_format }}</div>
          </div>
          <div class="rule-card__section" v-if="rule.score_composition">
            <div class="rule-card__label">成绩构成</div>
            <div class="rule-card__text">{{ rule.score_composition }}</div>
          </div>
          <div class="rule-card__section" v-if="rule.retest_content">
            <div class="rule-card__label">复试内容</div>
            <div class="rule-card__text">{{ rule.retest_content }}</div>
          </div>
          <div class="rule-card__section" v-if="rule.other_requirements">
            <div class="rule-card__label">其他要求</div>
            <div class="rule-card__text">{{ rule.other_requirements }}</div>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled, MoreFilled, Search, VideoPlay, VideoPause, Filter, Link, MagicStick, WarningFilled } from '@element-plus/icons-vue'
import ConfettiEffect from './ConfettiEffect.vue'
import { useDialog } from '../composables/useDialog'

const emit = defineEmits(['open-settings'])
const { isMobile, dialogWidth } = useDialog('720px')

const visible = ref(false)
const crawling = ref(false)
const aiAvailable = ref(false)
const confetti = ref(null)
let triggerElement = null
const university = ref('')
const year = ref(2026)
const majors = ref([])
const commonMajors = [
  '计算机科学与技术', '软件工程', '人工智能', '电子信息', '信息与通信工程',
  '控制科学与工程', '电气工程', '机械工程', '数学', '物理学',
]
const extractType = ref('admission_list')
const steps = ref([])
const finalResult = ref(null)

// 人工采集相关
const crawlMode = ref('auto')
const crawlModeOptions = [
  { label: '自动采集', value: 'auto' },
  { label: '指定网址', value: 'manual' },
]
const manualUrl = ref('')
const manualUniversity = ref('')
const manualLoading = ref(false)
const manualResult = ref(null)

// 采集类型选项
const autoExtractOptions = [
  { label: '录取名单', value: 'admission_list' },
  { label: '招生目录', value: 'program_catalog' },
]
const manualExtractOptions = [
  { label: '复试名单', value: 'retest_list' },
  { label: '拟录取名单', value: 'admission_list' },
  { label: '招生目录', value: 'program_catalog' },
  { label: '复试细则', value: 'retest_rules' },
]
const currentExtractOptions = computed(() =>
  crawlMode.value === 'manual' ? manualExtractOptions : autoExtractOptions
)

// 切换模式时重置采集类型
watch(crawlMode, (newMode) => {
  const validValues = newMode === 'manual'
    ? manualExtractOptions.map(o => o.value)
    : autoExtractOptions.map(o => o.value)
  if (!validValues.includes(extractType.value)) {
    extractType.value = validValues[0]
  }
})

let abortController = null
let timerInterval = null
const elapsedSeconds = ref(0)

const canStart = computed(() => university.value.trim() && aiAvailable.value && !crawling.value)

// 成功消息 - 根据数据量和类型变化
const successTitles = ['采集完成', '数据到手', '任务完成', '搞定！']
const successTitle = computed(() => {
  const count = totalRecords.value
  if (count >= 100) return '收获满满！'
  if (count >= 50) return '采集完成'
  return successTitles[Math.floor(Math.random() * successTitles.length)]
})

const successDataType = computed(() => {
  const type = extractType.value
  if (type === 'program_catalog') return '招生目录'
  if (type === 'retest_rules') return '复试细则'
  if (type === 'retest_list') return '复试名单'
  return '录取'
})

const successSuffix = computed(() => {
  const count = totalRecords.value
  if (count >= 100) return '，数据量很可观'
  if (count >= 50) return ''
  if (count >= 10) return '，继续加油'
  return ''
})

const elapsedTime = computed(() => {
  const s = elapsedSeconds.value
  const m = Math.floor(s / 60)
  return m > 0 ? `${m}分${(s % 60).toString().padStart(2, '0')}秒` : `${s}秒`
})

const pageCount = computed(() => {
  const match = steps.value.filter(s => s.status === 'done' && s.detail?.includes('已访问')).pop()
  if (match) {
    const m = match.detail.match(/已访问\s*(\d+)/)
    return m ? m[1] : '...'
  }
  return steps.value.filter(s => s.status === 'done').length
})

const foundCount = computed(() => {
  if (finalResult.value?.results) return finalResult.value.results.reduce((s, r) => s + (r.saved_count || r.count || 0), 0)
  return steps.value.filter(s => s.status === 'done' && s.detail?.includes('成功提取')).length
})

const progressPercent = computed(() => {
  if (finalResult.value) return 100
  if (!steps.value.length) return 0
  const done = steps.value.filter(s => s.status === 'done' || s.status === 'error').length
  return Math.min(95, Math.round((done / Math.max(steps.value.length, 1)) * 100))
})

const totalRecords = computed(() => {
  if (!finalResult.value?.results) return 0
  return finalResult.value.results.reduce((s, r) => s + (r.saved_count || r.count || 0), 0)
})

const errorMessage = computed(() => {
  if (!finalResult.value) return ''
  if (finalResult.value.errors?.length) return finalResult.value.errors[0]
  const failed = steps.value.filter(s => s.status === 'error')
  if (failed.length) return failed[failed.length - 1].detail || failed[failed.length - 1].step
  return '采集失败'
})

const openSettings = () => { visible.value = false; emit('open-settings') }

const checkStatus = async () => {
  try {
    const { data } = await axios.get('/api/ai-status', { params: { t: Date.now() } })
    aiAvailable.value = data.available
  } catch { aiAvailable.value = false }
}

onMounted(checkStatus)

const startCrawl = async () => {
  if (!university.value.trim()) return
  crawling.value = true
  finalResult.value = null
  steps.value = []
  elapsedSeconds.value = 0
  timerInterval = setInterval(() => { elapsedSeconds.value++ }, 1000)
  abortController = new AbortController()

  try {
    const resp = await fetch('/api/auto-crawl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ university: university.value.trim(), year: year.value, major: majors.value.join('、'), extract_type: extractType.value }),
      signal: abortController.signal,
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const processLines = (lines) => {
      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) { eventType = line.slice(7).trim() }
        else if (line.startsWith('data: ')) {
          const raw = line.slice(6)
          if (!raw) continue
          try { handleSSEEvent(eventType, JSON.parse(raw)) } catch (e) { console.warn('SSE JSON解析失败:', raw, e) }
          eventType = ''
        }
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      processLines(lines)
    }

    // 处理buffer中残留数据
    if (buffer.trim()) {
      processLines(buffer.split('\n'))
    }
  } catch (e) {
    if (e.name !== 'AbortError') ElMessage.error('采集请求失败: ' + e.message)
  } finally {
    crawling.value = false
    abortController = null
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null }
  }
}

const handleSSEEvent = (eventType, data) => {
  if (eventType === 'step') {
    const idx = steps.value.findIndex(s => s.step === data.step)
    if (idx >= 0) steps.value[idx] = data
    else steps.value.push(data)
  } else if (eventType === 'result') {
    finalResult.value = data
    if (data.success) {
      const count = data.results?.reduce((s, r) => s + (r.saved_count || r.count || 0), 0) || 0
      ElMessage.success(`采集成功！共获取 ${count} 条数据`)
      if (count >= 20) confetti.value?.show()
    }
  }
}

const cancelCrawl = () => {
  if (abortController) { abortController.abort(); ElMessage.info('已停止采集') }
}

const startManual = async () => {
  if (!manualUrl.value.trim()) return
  manualLoading.value = true
  manualResult.value = null
  steps.value = []
  elapsedSeconds.value = 0
  timerInterval = setInterval(() => { elapsedSeconds.value++ }, 1000)

  try {
    const resp = await fetch('/api/manual-extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: manualUrl.value.trim(),
        university: manualUniversity.value.trim(),
        extract_type: extractType.value,
      }),
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const processLines = (lines) => {
      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) { eventType = line.slice(7).trim() }
        else if (line.startsWith('data: ')) {
          const raw = line.slice(6)
          if (!raw) continue
          try {
            const data = JSON.parse(raw)
            if (eventType === 'step') {
              const idx = steps.value.findIndex(s => s.step === data.step)
              if (idx >= 0) steps.value[idx] = data
              else steps.value.push(data)
            } else if (eventType === 'result') {
              manualResult.value = data
              if (data.success) {
                ElMessage.success(`提取成功！共获取 ${data.count} 条数据`)
                if (data.count >= 20) confetti.value?.show()
              }
            }
          } catch (e) { console.warn('SSE JSON解析失败:', raw, e) }
          eventType = ''
        }
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      processLines(lines)
    }
    if (buffer.trim()) processLines(buffer.split('\n'))
  } catch (e) {
    manualResult.value = { success: false, error: e.message }
    ElMessage.error('提取失败: ' + e.message)
  } finally {
    manualLoading.value = false
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null }
  }
}

const open = async () => {
  triggerElement = document.activeElement
  visible.value = true
  finalResult.value = null
  manualResult.value = null
  steps.value = []
  university.value = ''
  year.value = 2026
  majors.value = []
  manualUrl.value = ''
  manualUniversity.value = ''
  crawlMode.value = 'auto'
  extractType.value = 'admission_list'
  await checkStatus()
}

const onDialogClose = () => {
  if (crawling.value) {
    cancelCrawl()
  }
  if (triggerElement) {
    triggerElement.focus()
    triggerElement = null
  }
}

onBeforeUnmount(() => {
  if (timerInterval) clearInterval(timerInterval)
  if (abortController) abortController.abort()
})

defineExpose({ open, checkStatus })
</script>

<style scoped>
/* ── 功能切换 ── */
.crawl-tabs {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

/* ── 模式选择 ── */
.crawl-mode {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

/* ── 输入区域 ── */
.crawl-input {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  background: var(--surface-tinted);
  border-radius: var(--radius-lg);
}

.crawl-input__row {
  display: flex;
  gap: var(--space-3);
}

.crawl-input__uni {
  flex: 1;
}

.crawl-input__year {
  width: 130px;
}

.crawl-input__majors {
  width: 100%;
}

.crawl-input__btn {
  width: 100%;
  height: 44px;
  font-size: var(--font-size-base);
  font-weight: 600;
  letter-spacing: 1px;
}

/* ── 进度概览 ── */
.crawl-stats {
  margin-top: var(--space-5);
  padding: var(--space-4) var(--space-5);
  background: var(--surface-tinted);
  border-radius: var(--radius-lg);
}

.crawl-stats__items {
  display: flex;
  justify-content: space-around;
  margin-bottom: var(--space-4);
}

.crawl-stats__item {
  text-align: center;
}

.crawl-stats__val {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-blue-600);
  line-height: 1.2;
}

.crawl-stats__label {
  font-size: var(--font-size-xs);
  color: var(--el-text-color-secondary);
  margin-top: var(--space-1);
}

.crawl-stats__bar {
  height: 4px;
  background: var(--el-border-color-lighter);
  border-radius: 2px;
  overflow: hidden;
}

.crawl-stats__fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-blue-500), var(--color-teal-500));
  border-radius: 2px;
  will-change: width;
  transition: width 0.6s cubic-bezier(0.25, 1, 0.5, 1);
}

/* ── 时间线 ── */
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
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--el-border-color);
  background: var(--el-bg-color);
  font-size: 14px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  will-change: border-color, background-color, color;
  transition: border-color 0.25s ease, background-color 0.25s ease, color 0.25s ease;
}

.tl-item--done .tl-dot {
  border-color: var(--color-green-500);
  color: var(--color-green-500);
  background: var(--color-green-50);
}

.tl-item--error .tl-dot {
  border-color: var(--el-color-danger);
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.tl-item--running .tl-dot {
  border-color: var(--color-blue-500);
  background: var(--color-blue-50);
  color: var(--color-blue-500);
}

.tl-pulse {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 2px solid var(--color-blue-500);
  animation: pulse 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
}

@keyframes pulse {
  0% { transform: scale(0.85); opacity: 0.7; }
  100% { transform: scale(1.5); opacity: 0; }
}

.tl-spin {
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-blue-200, #bfdbfe);
  border-top-color: var(--color-blue-500);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tl-line {
  position: absolute;
  left: 11px;
  top: 28px;
  bottom: -4px;
  width: 2px;
  background: var(--el-border-color-lighter);
  transition: background 0.3s ease;
}

.tl-line--done {
  background: var(--color-green-500);
}

.tl-item--running .tl-line {
  background: var(--color-blue-200);
}

.tl-body {
  flex: 1;
  padding-bottom: 20px;
  min-width: 0;
}

.tl-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.tl-title {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.tl-tag {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 1px var(--space-2);
  border-radius: 10px;
  line-height: 18px;
}

.tl-tag--run {
  background: var(--color-blue-50);
  color: var(--color-blue-600);
  animation: blink 2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.tl-tag--ok {
  background: var(--color-green-50);
  color: var(--color-green-500);
}

.tl-tag--err {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.tl-detail {
  font-size: var(--font-size-sm);
  color: var(--el-text-color-secondary);
  margin-top: var(--space-1);
  word-break: break-all;
  line-height: 1.5;
}

/* ── 结果 ── */
.crawl-result {
  margin-top: var(--space-5);
  animation: fade-up 0.35s ease;
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.crawl-result__banner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-lg);
}

.crawl-result__banner--ok {
  background: linear-gradient(135deg, var(--color-green-50), var(--color-teal-50));
  border: 1px solid var(--color-green-500);
}

.crawl-result__banner--celebrate {
  animation: celebrate 0.5s ease;
}

@keyframes celebrate {
  0% { transform: scale(0.95); opacity: 0; }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); opacity: 1; }
}

.crawl-result__banner--fail {
  background: var(--el-color-danger-light-9);
  border: 1px solid var(--el-color-danger);
}

.crawl-result__banner--warn {
  background: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning);
}

.crawl-result__icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.crawl-result__banner--ok .crawl-result__icon {
  background: var(--color-green-500);
  color: #fff;
}

.crawl-result__banner--fail .crawl-result__icon {
  background: var(--el-color-danger);
  color: #fff;
}

.crawl-result__banner--warn .crawl-result__icon {
  background: var(--el-color-warning);
  color: #fff;
}

.crawl-result__title {
  font-size: var(--font-size-base);
  font-weight: 700;
}

.crawl-result__desc {
  font-size: var(--font-size-sm);
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.crawl-result__desc strong {
  color: var(--color-green-500);
  font-size: var(--font-size-base);
}

.crawl-result__err {
  color: var(--el-color-danger);
  font-size: var(--font-size-sm);
  margin: var(--space-1) 0;
}

.crawl-result__cards {
  margin-top: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.res-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.res-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--surface-tinted);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.res-card__title {
  font-weight: 600;
  font-size: var(--font-size-base);
}

.res-card__count {
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-green-500);
  background: var(--color-green-50);
  padding: 2px var(--space-3);
  border-radius: 10px;
}

.res-card__src {
  font-size: var(--font-size-xs);
  color: var(--el-text-color-secondary);
  padding: var(--space-2) var(--space-4) 0;
}

/* ── 复试细则结果 ── */
.rules-result {
  margin-top: var(--space-3);
}

.rule-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-bottom: var(--space-3);
}

.rule-card__title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 var(--space-2) 0;
}

.rule-card__info {
  font-size: var(--font-size-sm);
  color: var(--el-text-color-secondary);
  margin-bottom: var(--space-3);
}

.rule-card__section {
  margin-bottom: var(--space-3);
}

.rule-card__label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-blue-600);
  margin-bottom: var(--space-1);
}

.rule-card__text {
  font-size: var(--font-size-sm);
  color: var(--el-text-color-regular);
  line-height: 1.6;
  white-space: pre-wrap;
}

/* ── 动态系统提示 ── */
.dynamic-tip {
  margin-top: var(--space-3);
  padding: var(--space-4);
  background: var(--surface-tinted);
  border-radius: var(--radius-lg);
}

.dynamic-tip p {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--font-size-sm);
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.dynamic-tip p:last-child {
  margin-bottom: 0;
}

.dynamic-tip a {
  color: var(--color-blue-600);
  text-decoration: none;
}

.dynamic-tip a:hover {
  text-decoration: underline;
}

.dynamic-tip__options {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--el-border-color-lighter);
}

.dynamic-tip__list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.dynamic-tip__tag {
  font-size: var(--font-size-xs);
}

.dynamic-tip__more {
  font-size: var(--font-size-xs);
  color: var(--el-text-color-secondary);
  line-height: 28px;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .crawl-input__row {
    flex-direction: column;
  }

  .crawl-input__year {
    width: 100%;
  }

  .crawl-stats__val {
    font-size: 18px;
  }

  .crawl-result__banner {
    padding: 12px 16px;
    gap: 12px;
  }
}
</style>
