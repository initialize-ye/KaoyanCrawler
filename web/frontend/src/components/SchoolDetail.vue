<template>
  <div class="school-detail">
    <!-- 返回按钮和学校标题 -->
    <div class="school-detail__header">
      <el-button @click="$emit('back')" text>
        <el-icon><ArrowLeft /></el-icon>
        返回列表
      </el-button>
      <h2 class="school-detail__title">{{ schoolName }}</h2>
      <el-button type="danger" plain size="small" @click="$emit('delete', schoolName)">
        <el-icon><Delete /></el-icon>
        删除学校
      </el-button>
    </div>

    <!-- 学校信息卡片 -->
    <div v-if="schoolInfo" class="school-header">
      <div class="school-header__main">
        <h2 class="school-name">{{ schoolInfo.name }}</h2>
        <a v-if="schoolInfo.website" :href="schoolInfo.website" target="_blank" class="school-website">
          <el-icon><Link /></el-icon>
          研究生院官网
        </a>
      </div>
      <div class="school-meta">
        <div v-if="schoolInfo.duration" class="meta-item">
          <span class="meta-label">学制</span>
          <span class="meta-value">{{ schoolInfo.duration }}</span>
        </div>
        <div v-if="schoolInfo.tuition" class="meta-item">
          <span class="meta-label">学费</span>
          <span class="meta-value">{{ schoolInfo.tuition }}</span>
        </div>
        <div v-if="schoolInfo.scholarship" class="meta-item">
          <span class="meta-label">奖学金</span>
          <span class="meta-value">{{ schoolInfo.scholarship }}</span>
        </div>
      </div>
    </div>

    <!-- 招生目录 -->
    <div v-if="subjects.length" class="section-card">
      <h3 class="section-title">招生目录</h3>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>学院</th>
              <th>专业代码</th>
              <th>专业名称</th>
              <th>招生人数</th>
              <th>初试科目</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in subjects" :key="row.id">
              <td>{{ row.department || '-' }}</td>
              <td class="code-cell">{{ row.major_code || '-' }}</td>
              <td>{{ row.major_name || '-' }}</td>
              <td class="num-cell">{{ row.enrollment || '-' }}</td>
              <td class="subjects-cell">
                <span v-if="row.subject1 || row.subject2 || row.subject3 || row.subject4">
                  {{ [row.subject1, row.subject2, row.subject3, row.subject4].filter(Boolean).join('、') }}
                </span>
                <span v-else class="muted">-</span>
              </td>
              <td>
                <el-button type="danger" text size="small" @click="deleteSubject(row.id)">删除</el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 录取数据 -->
    <div v-if="admissions.length" class="section-card">
      <h3 class="section-title">录取数据</h3>
      <div class="table-scroll">
        <table class="data-table">
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
                <el-tag :type="row.list_type === '录取名单' ? 'success' : 'warning'" size="small">
                  {{ row.list_type }}
                </el-tag>
              </td>
              <td>{{ row.major || '-' }}</td>
              <td>{{ row.name || '-' }}</td>
              <td class="code-cell">{{ row.exam_id || '-' }}</td>
              <td class="num-cell">{{ row.initial_score || '-' }}</td>
              <td class="num-cell">{{ row.retest_score || '-' }}</td>
              <td class="num-cell">{{ row.total_score || '-' }}</td>
              <td>{{ row.admission_status || '-' }}</td>
              <td>
                <el-button type="danger" text size="small" @click="deleteAdmission(row.id)">删除</el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 复试细则 -->
    <div v-if="rules.length" class="section-card">
      <h3 class="section-title">复试细则</h3>
      <div class="rules-list">
        <div v-for="rule in rules" :key="rule.id" class="rule-card">
          <div class="rule-card__header">
            <h4>{{ rule.title }}</h4>
            <el-button type="danger" text size="small" @click="deleteRule(rule.id)">删除</el-button>
          </div>
          <div v-if="rule.department || rule.major" class="rule-card__meta">
            <span v-if="rule.department">{{ rule.department }}</span>
            <span v-if="rule.major"> · {{ rule.major }}</span>
          </div>
          <div v-if="rule.content_summary" class="rule-card__section">
            <div class="rule-card__label">内容摘要</div>
            <div class="rule-card__text">{{ rule.content_summary }}</div>
          </div>
          <div v-if="rule.retest_format" class="rule-card__section">
            <div class="rule-card__label">复试形式</div>
            <div class="rule-card__text">{{ rule.retest_format }}</div>
          </div>
          <div v-if="rule.score_composition" class="rule-card__section">
            <div class="rule-card__label">成绩构成</div>
            <div class="rule-card__text">{{ rule.score_composition }}</div>
          </div>
          <div v-if="rule.retest_content" class="rule-card__section">
            <div class="rule-card__label">复试内容</div>
            <div class="rule-card__text">{{ rule.retest_content }}</div>
          </div>
          <div v-if="rule.other_requirements" class="rule-card__section">
            <div class="rule-card__label">其他要求</div>
            <div class="rule-card__text">{{ rule.other_requirements }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分数线 -->
    <div v-if="scoreLines.length" class="section-card">
      <h3 class="section-title">分数线</h3>
      <div class="table-scroll">
        <table class="data-table">
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
              <td class="code-cell">{{ row.discipline_code || '-' }}</td>
              <td class="num-cell">{{ row.total_score || '-' }}</td>
              <td class="num-cell">{{ row.score1 || '-' }}</td>
              <td class="num-cell">{{ row.score2 || '-' }}</td>
              <td>
                <el-button type="danger" text size="small" @click="deleteScoreLine(row.id)">删除</el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 无数据提示 -->
    <el-empty
      v-if="!subjects.length && !admissions.length && !rules.length && !scoreLines.length"
      description="暂无数据"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete, Link } from '@element-plus/icons-vue'

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
.school-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.school-detail__header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.school-detail__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  flex: 1;
}

/* 学校信息卡片 */
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

/* 数据区块 */
.section-card {
  background: var(--el-bg-color);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  overflow: hidden;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  padding: 16px 20px;
  margin: 0;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.table-scroll {
  overflow-x: auto;
  padding: 16px;
}

/* 表格样式 */
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
}

.data-table th {
  background: var(--el-fill-color-light);
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.data-table tbody tr:hover {
  background: var(--el-color-primary-light-9);
}

.code-cell {
  font-family: 'Consolas', 'Monaco', monospace;
  color: var(--el-text-color-secondary);
}

.num-cell {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.subjects-cell {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.muted {
  color: var(--el-text-color-placeholder);
}

/* 复试细则卡片 */
.rules-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.rule-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
}

.rule-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.rule-card__header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.rule-card__meta {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
}

.rule-card__section {
  margin-bottom: 12px;
}

.rule-card__section:last-child {
  margin-bottom: 0;
}

.rule-card__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
}

.rule-card__text {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  white-space: pre-wrap;
}

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

  .section-title {
    padding: 12px 16px;
  }

  .table-scroll {
    padding: 12px;
  }

  .data-table th,
  .data-table td {
    padding: 8px 10px;
    font-size: 12px;
  }

  .subjects-cell {
    max-width: 150px;
  }
}
</style>
