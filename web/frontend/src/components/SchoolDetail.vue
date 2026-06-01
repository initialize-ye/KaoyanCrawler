<template>
  <div class="school-detail">
    <!-- 返回按钮和学校标题 -->
    <div class="detail-header">
      <button class="back-btn" @click="$emit('back')">
        <span class="material-icons">arrow_back</span>
        <span>返回列表</span>
      </button>
      <h2 class="detail-title">{{ schoolName }}</h2>
      <button class="icon-btn icon-btn--danger" @click="$emit('delete', schoolName)" data-tooltip="删除学校">
        <span class="material-icons-outlined">delete_outline</span>
      </button>
    </div>

    <!-- 学校信息卡片 -->
    <div v-if="schoolInfo" class="info-card">
      <div class="info-card__main">
        <div class="info-card__icon">
          <span class="material-icons">school</span>
        </div>
        <div class="info-card__text">
          <h2 class="info-card__name">{{ schoolInfo.name }}</h2>
          <a v-if="schoolInfo.website" :href="schoolInfo.website" target="_blank" class="info-card__link">
            <span class="material-icons" style="font-size: 16px;">open_in_new</span>
            研究生院官网
          </a>
        </div>
      </div>
      <div class="info-card__meta" v-if="schoolInfo.duration || schoolInfo.tuition || schoolInfo.scholarship">
        <div class="meta-chip" v-if="schoolInfo.duration">
          <span class="material-icons-outlined" style="font-size: 16px;">schedule</span>
          {{ schoolInfo.duration }}
        </div>
        <div class="meta-chip" v-if="schoolInfo.tuition">
          <span class="material-icons-outlined" style="font-size: 16px;">payments</span>
          {{ schoolInfo.tuition }}
        </div>
        <div class="meta-chip" v-if="schoolInfo.scholarship">
          <span class="material-icons-outlined" style="font-size: 16px;">emoji_events</span>
          {{ schoolInfo.scholarship }}
        </div>
      </div>
    </div>

    <!-- 录取信息 -->
    <div v-if="subjects.length" class="data-section">
      <div class="section-header">
        <div class="section-header__left">
          <span class="material-icons-outlined section-header__icon">analytics</span>
          <h3 class="section-header__title">录取信息</h3>
          <span class="count-badge">{{ subjects.length }}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table class="google-table">
          <thead>
            <tr>
              <th>学院</th>
              <th>专业代码</th>
              <th>专业名称</th>
              <th>招生人数</th>
              <th>复试线</th>
              <th>复试人数</th>
              <th>录取人数</th>
              <th>复录比</th>
              <th>最低分</th>
              <th>平均分</th>
              <th>最高分</th>
              <th>初试科目</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in subjects" :key="row.id">
              <td>{{ row.department || '-' }}</td>
              <td class="mono-cell">{{ row.major_code || '-' }}</td>
              <td class="name-cell">{{ row.major_name || '-' }}</td>
              <td class="num-cell">{{ row.enrollment || '-' }}</td>
              <td class="num-cell highlight-red">{{ row.retest_score_line || '-' }}</td>
              <td class="num-cell">{{ row.retest_count || '-' }}</td>
              <td class="num-cell">{{ row.admission_count || '-' }}</td>
              <td class="num-cell">{{ row.admission_ratio || '-' }}</td>
              <td class="num-cell">{{ row.admission_min_score || '-' }}</td>
              <td class="num-cell">{{ row.admission_avg_score || '-' }}</td>
              <td class="num-cell">{{ row.admission_max_score || '-' }}</td>
              <td class="subjects-cell">
                <span v-if="row.subject1 || row.subject2 || row.subject3 || row.subject4">
                  {{ [row.subject1, row.subject2, row.subject3, row.subject4].filter(Boolean).join('、') }}
                </span>
                <span v-else class="muted">-</span>
              </td>
              <td>
                <button class="icon-btn icon-btn--danger icon-btn--sm" @click="deleteSubject(row.id)">
                  <span class="material-icons" style="font-size: 18px;">delete_outline</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 录取数据 -->
    <div v-if="admissions.length" class="data-section">
      <div class="section-header">
        <div class="section-header__left">
          <span class="material-icons-outlined section-header__icon">people</span>
          <h3 class="section-header__title">录取数据</h3>
          <span class="count-badge">{{ admissions.length }}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table class="google-table">
          <thead>
            <tr>
              <th>类型</th>
              <th>专业</th>
              <th>姓名</th>
              <th>考生编号</th>
              <th>初试</th>
              <th>复试</th>
              <th>总分</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in admissions" :key="row.id">
              <td>
                <span class="status-tag" :class="row.list_type === '录取名单' ? 'status-tag--success' : 'status-tag--warning'">
                  {{ row.list_type }}
                </span>
              </td>
              <td>{{ row.major || '-' }}</td>
              <td>{{ row.name || '-' }}</td>
              <td class="mono-cell">{{ row.exam_id || '-' }}</td>
              <td class="num-cell">{{ row.initial_score || '-' }}</td>
              <td class="num-cell">{{ row.retest_score || '-' }}</td>
              <td class="num-cell">{{ row.total_score || '-' }}</td>
              <td>{{ row.admission_status || '-' }}</td>
              <td>
                <button class="icon-btn icon-btn--danger icon-btn--sm" @click="deleteAdmission(row.id)">
                  <span class="material-icons" style="font-size: 18px;">delete_outline</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 复试细则 -->
    <div v-if="rules.length" class="data-section">
      <div class="section-header">
        <div class="section-header__left">
          <span class="material-icons-outlined section-header__icon">description</span>
          <h3 class="section-header__title">复试细则</h3>
          <span class="count-badge">{{ rules.length }}</span>
        </div>
      </div>
      <div class="rules-grid">
        <div v-for="rule in rules" :key="rule.id" class="rule-card">
          <div class="rule-card__header">
            <h4 class="rule-card__title">{{ rule.title }}</h4>
            <button class="icon-btn icon-btn--danger icon-btn--sm" @click="deleteRule(rule.id)">
              <span class="material-icons" style="font-size: 18px;">delete_outline</span>
            </button>
          </div>
          <div v-if="rule.department || rule.major" class="rule-card__meta">
            <span v-if="rule.department">{{ rule.department }}</span>
            <span v-if="rule.major"> · {{ rule.major }}</span>
          </div>
          <div v-if="rule.content_summary" class="rule-card__field">
            <span class="rule-card__label">内容摘要</span>
            <p class="rule-card__value">{{ rule.content_summary }}</p>
          </div>
          <div v-if="rule.retest_format" class="rule-card__field">
            <span class="rule-card__label">复试形式</span>
            <p class="rule-card__value">{{ rule.retest_format }}</p>
          </div>
          <div v-if="rule.score_composition" class="rule-card__field">
            <span class="rule-card__label">成绩构成</span>
            <p class="rule-card__value">{{ rule.score_composition }}</p>
          </div>
          <div v-if="rule.retest_content" class="rule-card__field">
            <span class="rule-card__label">复试内容</span>
            <p class="rule-card__value">{{ rule.retest_content }}</p>
          </div>
          <div v-if="rule.other_requirements" class="rule-card__field">
            <span class="rule-card__label">其他要求</span>
            <p class="rule-card__value">{{ rule.other_requirements }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 分数线 -->
    <div v-if="scoreLines.length" class="data-section">
      <div class="section-header">
        <div class="section-header__left">
          <span class="material-icons-outlined section-header__icon">trending_up</span>
          <h3 class="section-header__title">分数线</h3>
          <span class="count-badge">{{ scoreLines.length }}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table class="google-table">
          <thead>
            <tr>
              <th>学位类别</th>
              <th>学科门类</th>
              <th>代码</th>
              <th>总分线</th>
              <th>单科1</th>
              <th>单科2</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in scoreLines" :key="row.id">
              <td>{{ row.category || '-' }}</td>
              <td>{{ row.discipline || '-' }}</td>
              <td class="mono-cell">{{ row.discipline_code || '-' }}</td>
              <td class="num-cell highlight-red">{{ row.total_score || '-' }}</td>
              <td class="num-cell">{{ row.score1 || '-' }}</td>
              <td class="num-cell">{{ row.score2 || '-' }}</td>
              <td>
                <button class="icon-btn icon-btn--danger icon-btn--sm" @click="deleteScoreLine(row.id)">
                  <span class="material-icons" style="font-size: 18px;">delete_outline</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 无数据提示 -->
    <div v-if="!subjects.length && !admissions.length && !rules.length && !scoreLines.length" class="empty-state">
      <span class="material-icons-outlined empty-state__icon">inbox</span>
      <p class="empty-state__text">暂无数据</p>
      <p class="empty-state__hint">点击右上角"采集"或"图片识别"添加数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps({
  schoolName: { type: String, required: true },
})

const emit = defineEmits(['back', 'delete', 'refresh'])

const schoolInfo = ref(null)
const subjects = ref([])
const admissions = ref([])
const rules = ref([])
const scoreLines = ref([])

const fetchData = async () => {
  if (!props.schoolName) return

  try {
    const schoolResp = await axios.get(`/api/schools/${encodeURIComponent(props.schoolName)}`)
    schoolInfo.value = schoolResp.data

    const [subjResp, admResp, rulesResp, slResp] = await Promise.all([
      axios.get('/api/subjects', { params: { university: props.schoolName, page_size: 200 } }),
      axios.get('/api/admissions', { params: { university: props.schoolName, page_size: 200 } }),
      axios.get('/api/retest-rules', { params: { university: props.schoolName, page_size: 200 } }),
      axios.get('/api/score-lines', { params: { university: props.schoolName, page_size: 200 } }),
    ])

    subjects.value = subjResp.data.data || []
    admissions.value = admResp.data.data || []
    rules.value = rulesResp.data.data || []
    scoreLines.value = slResp.data.data || []
  } catch (e) {
    const errDetail = e.response?.data?.detail
    const errMsg = typeof errDetail === 'string' ? errDetail : e.message || '未知错误'
    ElMessage.error('获取学校数据失败: ' + errMsg)
  }
}

const deleteSubject = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此条记录？', '确认删除', { type: 'warning' })
    await axios.delete(`/api/subjects/${id}`)
    ElMessage.success('已删除')
    fetchData()
    emit('refresh')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const deleteAdmission = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此条记录？', '确认删除', { type: 'warning' })
    await axios.delete(`/api/admissions/${id}`)
    ElMessage.success('已删除')
    fetchData()
    emit('refresh')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const deleteRule = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此条记录？', '确认删除', { type: 'warning' })
    await axios.delete(`/api/retest-rules/${id}`)
    ElMessage.success('已删除')
    fetchData()
    emit('refresh')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const deleteScoreLine = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此条记录？', '确认删除', { type: 'warning' })
    await axios.delete(`/api/score-lines/${id}`)
    ElMessage.success('已删除')
    fetchData()
    emit('refresh')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

watch(() => props.schoolName, fetchData)
onMounted(fetchData)
</script>

<style scoped>
/* ── Header ── */
.detail-header {
  display: flex;
  align-items: center;
  gap: var(--google-space-4);
  margin-bottom: var(--google-space-6);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: var(--google-space-1);
  padding: var(--google-space-2) var(--google-space-3);
  border: none;
  background: transparent;
  color: var(--google-blue);
  font-family: var(--google-font);
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--google-radius-full);
  cursor: pointer;
  transition: all var(--google-transition-fast);
}

.back-btn:hover {
  background: var(--google-blue-bg);
}

.back-btn .material-icons {
  font-size: 20px;
}

.detail-title {
  flex: 1;
  font-family: var(--google-font);
  font-size: 22px;
  font-weight: 400;
  color: var(--google-text-primary);
  margin: 0;
}

/* ── Icon Button ── */
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  color: var(--google-text-secondary);
  border-radius: var(--google-radius-full);
  cursor: pointer;
  transition: all var(--google-transition-fast);
}

.icon-btn:hover {
  background: var(--google-gray-100);
  color: var(--google-text-primary);
}

.icon-btn--danger:hover {
  background: #fce8e6;
  color: var(--google-red);
}

.icon-btn--sm {
  width: 32px;
  height: 32px;
}

/* ── Info Card ── */
.info-card {
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  padding: var(--google-space-6);
  margin-bottom: var(--google-space-6);
  animation: google-fade-in 0.3s ease-out;
}

.info-card__main {
  display: flex;
  align-items: center;
  gap: var(--google-space-4);
  margin-bottom: var(--google-space-4);
}

.info-card__icon {
  width: 48px;
  height: 48px;
  background: var(--google-blue-bg);
  border-radius: var(--google-radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--google-blue);
  font-size: 28px;
  flex-shrink: 0;
}

.info-card__text {
  flex: 1;
}

.info-card__name {
  font-family: var(--google-font);
  font-size: 24px;
  font-weight: 400;
  color: var(--google-text-primary);
  margin: 0 0 4px;
}

.info-card__link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--google-blue);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: var(--google-radius-full);
  transition: all var(--google-transition-fast);
}

.info-card__link:hover {
  background: var(--google-blue-bg);
}

.info-card__meta {
  display: flex;
  gap: var(--google-space-3);
  flex-wrap: wrap;
}

.meta-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  background: var(--google-gray-50);
  border: 1px solid var(--google-gray-200);
  border-radius: var(--google-radius-full);
  font-size: 13px;
  color: var(--google-text-secondary);
}

/* ── Data Section ── */
.data-section {
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  margin-bottom: var(--google-space-6);
  overflow: hidden;
  animation: google-fade-in 0.3s ease-out;
}

.section-header {
  padding: var(--google-space-4) var(--google-space-6);
  border-bottom: 1px solid var(--google-gray-200);
}

.section-header__left {
  display: flex;
  align-items: center;
  gap: var(--google-space-3);
}

.section-header__icon {
  color: var(--google-blue);
  font-size: 22px;
}

.section-header__title {
  font-family: var(--google-font);
  font-size: 16px;
  font-weight: 500;
  color: var(--google-text-primary);
  margin: 0;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  background: var(--google-blue-bg);
  color: var(--google-blue);
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--google-radius-full);
}

/* ── Table ── */
.table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.google-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--google-font-roboto);
  font-size: 13px;
}

.google-table th {
  background: var(--google-gray-50);
  color: var(--google-text-secondary);
  font-weight: 500;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 16px;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--google-gray-200);
  position: sticky;
  top: 0;
}

.google-table td {
  padding: 12px 16px;
  color: var(--google-text-primary);
  border-bottom: 1px solid var(--google-gray-100);
}

.google-table tbody tr:hover {
  background: var(--google-gray-50);
}

.google-table tbody tr:last-child td {
  border-bottom: none;
}

.mono-cell {
  font-family: 'Roboto Mono', 'Consolas', monospace;
  color: var(--google-text-secondary);
  font-size: 12px;
}

.name-cell {
  font-weight: 500;
}

.num-cell {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.highlight-red {
  color: var(--google-red);
  font-weight: 600;
}

.subjects-cell {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.muted {
  color: var(--google-text-tertiary);
}

/* ── Status Tags ── */
.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: var(--google-radius-full);
  font-size: 12px;
  font-weight: 500;
}

.status-tag--success {
  background: var(--google-green-bg);
  color: var(--google-green-dark);
}

.status-tag--warning {
  background: #fef7e0;
  color: var(--google-yellow-dark);
}

/* ── Rules Grid ── */
.rules-grid {
  display: flex;
  flex-direction: column;
  gap: var(--google-space-4);
  padding: var(--google-space-6);
}

.rule-card {
  border: 1px solid var(--google-gray-200);
  border-radius: var(--google-radius-sm);
  padding: var(--google-space-4) var(--google-space-5);
  transition: border-color var(--google-transition-fast);
}

.rule-card:hover {
  border-color: var(--google-gray-300);
}

.rule-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--google-space-3);
  margin-bottom: var(--google-space-2);
}

.rule-card__title {
  margin: 0;
  font-family: var(--google-font);
  font-size: 15px;
  font-weight: 500;
  color: var(--google-text-primary);
}

.rule-card__meta {
  font-size: 13px;
  color: var(--google-text-tertiary);
  margin-bottom: var(--google-space-3);
}

.rule-card__field {
  margin-bottom: var(--google-space-3);
}

.rule-card__field:last-child {
  margin-bottom: 0;
}

.rule-card__label {
  display: inline-block;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--google-blue);
  background: var(--google-blue-bg);
  padding: 2px 8px;
  border-radius: var(--google-radius-sm);
  margin-bottom: 4px;
}

.rule-card__value {
  margin: 0;
  font-size: 13px;
  color: var(--google-text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
}

/* ── Empty State ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: var(--google-surface);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  animation: google-fade-in 0.3s ease-out;
}

.empty-state__icon {
  font-size: 64px;
  color: var(--google-gray-300);
  margin-bottom: var(--google-space-4);
}

.empty-state__text {
  font-family: var(--google-font);
  font-size: 18px;
  color: var(--google-text-secondary);
  margin: 0 0 8px;
}

.empty-state__hint {
  font-size: 14px;
  color: var(--google-text-tertiary);
  margin: 0;
}

/* ── Animation ── */
@keyframes google-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .detail-header {
    gap: var(--google-space-2);
  }

  .detail-title {
    font-size: 18px;
  }

  .info-card {
    padding: var(--google-space-4);
  }

  .info-card__main {
    gap: var(--google-space-3);
  }

  .info-card__name {
    font-size: 20px;
  }

  .section-header {
    padding: var(--google-space-3) var(--google-space-4);
  }

  .google-table th,
  .google-table td {
    padding: 8px 12px;
    font-size: 12px;
  }

  .subjects-cell {
    max-width: 150px;
  }

  .rules-grid {
    padding: var(--google-space-4);
  }
}
</style>
