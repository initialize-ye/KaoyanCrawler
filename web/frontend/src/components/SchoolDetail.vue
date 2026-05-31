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
    <div v-if="schoolInfo" class="info-card">
      <el-descriptions :column="isMobile ? 1 : 2" border size="small">
        <el-descriptions-item label="学校名称">{{ schoolInfo.name }}</el-descriptions-item>
        <el-descriptions-item label="官网">
          <a v-if="schoolInfo.website" :href="schoolInfo.website" target="_blank" class="link">
            {{ schoolInfo.website }}
          </a>
          <span v-else class="muted">未填写</span>
        </el-descriptions-item>
        <el-descriptions-item label="学制">{{ schoolInfo.duration || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="学费">{{ schoolInfo.tuition || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="奖学金" :span="2">{{ schoolInfo.scholarship || '未填写' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 数据标签页 -->
    <el-tabs v-model="activeTab" class="data-tabs">
      <el-tab-pane label="招生目录" name="subjects">
        <div v-if="subjects.length" class="table-scroll">
          <el-table :data="subjects" stripe border size="small" max-height="500">
            <el-table-column prop="department" label="学院" min-width="120" show-overflow-tooltip />
            <el-table-column prop="major_code" label="专业代码" width="100" />
            <el-table-column prop="major_name" label="专业名称" min-width="140" show-overflow-tooltip />
            <el-table-column prop="enrollment" label="招生人数" width="80" align="center" />
            <el-table-column prop="subject1" label="科目1" min-width="100" show-overflow-tooltip />
            <el-table-column prop="subject2" label="科目2" min-width="100" show-overflow-tooltip />
            <el-table-column prop="subject3" label="科目3" min-width="100" show-overflow-tooltip />
            <el-table-column prop="subject4" label="科目4" min-width="100" show-overflow-tooltip />
            <el-table-column label="操作" width="60">
              <template #default="{ row }">
                <el-button type="danger" text size="small" @click="deleteSubject(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="暂无招生目录数据" />
      </el-tab-pane>

      <el-tab-pane label="录取数据" name="admissions">
        <div v-if="admissions.length" class="table-scroll">
          <el-table :data="admissions" stripe border size="small" max-height="500">
            <el-table-column prop="list_type" label="类型" width="90" />
            <el-table-column prop="major" label="专业" min-width="140" show-overflow-tooltip />
            <el-table-column prop="name" label="姓名" width="80" />
            <el-table-column prop="exam_id" label="考生编号" width="120" />
            <el-table-column prop="initial_score" label="初试" width="70" align="center" />
            <el-table-column prop="retest_score" label="复试" width="70" align="center" />
            <el-table-column prop="total_score" label="总分" width="70" align="center" />
            <el-table-column prop="admission_status" label="状态" width="80" />
            <el-table-column label="操作" width="60">
              <template #default="{ row }">
                <el-button type="danger" text size="small" @click="deleteAdmission(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="暂无录取数据" />
      </el-tab-pane>

      <el-tab-pane label="复试细则" name="rules">
        <div v-if="rules.length" class="rules-list">
          <div v-for="rule in rules" :key="rule.id" class="rule-card">
            <div class="rule-card__header">
              <h4>{{ rule.title }}</h4>
              <el-button type="danger" text size="small" @click="deleteRule(rule.id)">删除</el-button>
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
          </div>
        </div>
        <el-empty v-else description="暂无复试细则" />
      </el-tab-pane>

      <el-tab-pane label="分数线" name="score_lines">
        <div v-if="scoreLines.length" class="table-scroll">
          <el-table :data="scoreLines" stripe border size="small" max-height="500">
            <el-table-column prop="category" label="学位类别" width="100" />
            <el-table-column prop="discipline" label="学科门类" min-width="120" />
            <el-table-column prop="discipline_code" label="代码" width="80" />
            <el-table-column prop="total_score" label="总分线" width="80" align="center" />
            <el-table-column prop="score1" label="单科1" width="70" align="center" />
            <el-table-column prop="score2" label="单科2" width="70" align="center" />
            <el-table-column label="操作" width="60">
              <template #default="{ row }">
                <el-button type="danger" text size="small" @click="deleteScoreLine(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="暂无分数线数据" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete } from '@element-plus/icons-vue'
import { useResponsive } from '../composables/useResponsive'

const props = defineProps({
  schoolName: { type: String, required: true },
})

const emit = defineEmits(['back', 'delete', 'refresh'])

const { isMobile } = useResponsive()

const activeTab = ref('subjects')
const schoolInfo = ref(null)
const subjects = ref([])
const admissions = ref([])
const rules = ref([])
const scoreLines = ref([])

const fetchData = async () => {
  if (!props.schoolName) return

  try {
    // 获取学校信息
    const schoolResp = await axios.get(`/api/schools/${encodeURIComponent(props.schoolName)}`)
    schoolInfo.value = schoolResp.data

    // 获取各表数据
    const [subjResp, admResp, rulesResp, slResp] = await Promise.all([
      axios.get('/api/subjects', { params: { university: props.schoolName, page_size: 1000 } }),
      axios.get('/api/admissions', { params: { university: props.schoolName, page_size: 1000 } }),
      axios.get('/api/retest-rules', { params: { university: props.schoolName, page_size: 1000 } }),
      axios.get('/api/score-lines', { params: { university: props.schoolName, page_size: 1000 } }),
    ])

    subjects.value = subjResp.data.data || []
    admissions.value = admResp.data.data || []
    rules.value = rulesResp.data.data || []
    scoreLines.value = slResp.data.data || []
  } catch (e) {
    ElMessage.error('获取学校数据失败: ' + (e.response?.data?.detail || e.message))
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

.info-card {
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  padding: 16px;
}

.data-tabs {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 16px;
}

.table-scroll {
  overflow-x: auto;
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
}

.rule-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
}

.rule-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.rule-card__header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.rule-card__section {
  margin-bottom: 8px;
}

.rule-card__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.rule-card__text {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
  white-space: pre-wrap;
}
</style>
