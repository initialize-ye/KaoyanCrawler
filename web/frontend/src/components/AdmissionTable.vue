<template>
  <div class="admission-table">
    <div class="table-header">
      <div class="table-header__left">
        <span class="table-header__title">录取数据</span>
        <el-tag type="info" size="small">{{ total }}</el-tag>
      </div>
    </div>

    <div class="table-scroll">
      <el-table :data="tableData" stripe style="width: 100%" v-loading="loading"
        :max-height="isMobile ? 350 : 500" empty-text="暂无数据，点击右上角开始采集">
        <el-table-column prop="university" label="学校" min-width="120" fixed />
        <el-table-column prop="year" label="年份" width="70" align="center" />
        <el-table-column prop="list_type" label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.list_type === '录取名单' ? 'success' : 'warning'" size="small" effect="dark">
              {{ row.list_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="major" label="专业" min-width="160" show-overflow-tooltip />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column prop="exam_id" label="考生编号" width="130" />
        <el-table-column prop="initial_score" label="初试" width="80" align="center">
          <template #default="{ row }">
            <span :class="scoreClass(row.initial_score)" :aria-label="row.initial_score ? `初试${row.initial_score}分` : '无数据'">{{ row.initial_score ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="retest_score" label="复试" width="80" align="center">
          <template #default="{ row }">
            <span :class="scoreClass(row.retest_score)" :aria-label="row.retest_score ? `复试${row.retest_score}分` : '无数据'">{{ row.retest_score ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_score" label="总分" width="80" align="center">
          <template #default="{ row }">
            <span :class="totalScoreClass(row.total_score)" :aria-label="row.total_score ? `总分${row.total_score}分` : '无数据'">{{ row.total_score ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="admission_status" label="状态" width="80">
          <template #default="{ row }">
            <span v-if="row.admission_status" :class="statusClass(row.admission_status)"
              :aria-label="`状态: ${row.admission_status}`">
              <span class="status-dot" :class="`status-dot--${statusClass(row.admission_status)}`"></span>
              {{ row.admission_status }}
            </span>
            <span v-else aria-label="无状态信息">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="admission_type" label="录取类别" width="90" />
      </el-table>
    </div>

    <div class="table-pagination">
      <el-pagination v-model:current-page="currentPage" :page-size="pageSize" :total="total"
        :layout="isMobile ? 'prev, pager, next' : 'total, prev, pager, next, jumper'"
        :small="isMobile" @current-change="onPageChange" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useResponsive } from '../composables/useResponsive'

const { isMobile } = useResponsive()

const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)

const scoreClass = (score) => {
  if (score == null) return ''
  if (score >= 380) return 'score-high'
  if (score >= 300) return 'score-mid'
  return 'score-low'
}

const totalScoreClass = (score) => {
  if (score == null) return ''
  if (score >= 400) return 'score-high'
  if (score >= 320) return 'score-mid'
  return 'score-low'
}

const statusClass = (status) => {
  if (!status) return ''
  if (status.includes('拟录取') || status.includes('录取')) return 'status-admitted'
  if (status.includes('候补') || status.includes('递补')) return 'status-waiting'
  return ''
}

let currentParams = {}

const fetchData = async (params = {}) => {
  loading.value = true
  currentParams = params
  try {
    const { data } = await axios.get('/api/admissions', {
      params: { ...params, page: currentPage.value, page_size: pageSize.value },
    })
    tableData.value = Array.isArray(data.data) ? data.data : []
    total.value = typeof data.total === 'number' ? data.total : 0
    // 如果当前页超出范围，修正到第一页
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = 1
      // 重新获取第一页数据
      const { data: newData } = await axios.get('/api/admissions', {
        params: { ...params, page: 1, page_size: pageSize.value },
      })
      tableData.value = Array.isArray(newData.data) ? newData.data : []
      total.value = typeof newData.total === 'number' ? newData.total : 0
    }
  } catch (e) {
    tableData.value = []
    total.value = 0
    ElMessage.error('获取数据失败: ' + (e.response?.data?.detail || e.message || '网络错误'))
  } finally {
    loading.value = false
  }
}

const onPageChange = (page) => {
  currentPage.value = page
  fetchData(currentParams)
}

onMounted(() => fetchData())
defineExpose({ fetchData })
</script>

<style scoped>
.admission-table {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.table-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-radius: 8px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

/* 分数样式 */
.score-high {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #67c23a;
  font-weight: 600;
  background: rgba(103, 194, 58, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.score-mid {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #e6a23c;
  font-weight: 500;
  background: rgba(230, 162, 60, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.score-low {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #909399;
  background: rgba(144, 147, 153, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 状态样式 */
.status-admitted {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #67c23a;
  font-weight: 600;
}

.status-waiting {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #e6a23c;
  font-weight: 500;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot--status-admitted {
  background: #67c23a;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.5);
}

.status-dot--status-waiting {
  background: #e6a23c;
  box-shadow: 0 0 8px rgba(230, 162, 60, 0.5);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 768px) {
  .table-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .table-pagination {
    justify-content: center;
  }
}

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.status-dot--status-admitted {
  background: var(--color-green-500);
}

.status-dot--status-waiting {
  background: var(--color-amber-500);
}

@media (max-width: 768px) {
  .table-pagination {
    justify-content: center;
  }
}
</style>
