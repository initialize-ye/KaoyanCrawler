<template>
  <div class="score-lines-table">
    <div class="table-header">
      <div class="table-header__left">
        <span class="table-header__title">分数线数据</span>
        <el-tag type="info" size="small">{{ total }}</el-tag>
      </div>
      <el-button type="primary" size="small" @click="exportData">
        <el-icon><Download /></el-icon>
        导出CSV
      </el-button>
    </div>

    <div class="table-scroll">
      <el-table :data="tableData" stripe style="width: 100%" v-loading="loading"
        :max-height="isMobile ? 350 : 500" empty-text="暂无数据，点击右上角开始采集">
        <el-table-column prop="university" label="学校" min-width="120" fixed />
        <el-table-column prop="year" label="年份" width="70" align="center" />
        <el-table-column prop="category" label="学位类别" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.category === '学术学位' ? 'primary' : 'success'" size="small">
              {{ row.category }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="discipline" label="学科门类" min-width="120" show-overflow-tooltip />
        <el-table-column prop="discipline_code" label="学科代码" width="100" align="center" />
        <el-table-column prop="total_score" label="总分线" width="80" align="center">
          <template #default="{ row }">
            <span :class="scoreClass(row.total_score)">{{ row.total_score ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="score1" label="单科1" width="80" align="center">
          <template #default="{ row }">
            <span>{{ row.score1 ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="score2" label="单科2" width="80" align="center">
          <template #default="{ row }">
            <span>{{ row.score2 ?? '-' }}</span>
          </template>
        </el-table-column>
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
import { Download } from '@element-plus/icons-vue'
import { useResponsive } from '../composables/useResponsive'

const { isMobile } = useResponsive()

const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)

const scoreClass = (score) => {
  if (score == null) return ''
  if (score >= 350) return 'score-high'
  if (score >= 300) return 'score-mid'
  return 'score-low'
}

let currentParams = {}

const fetchData = async (params = {}) => {
  loading.value = true
  currentParams = params
  try {
    const { data } = await axios.get('/api/score-lines', {
      params: { ...params, page: currentPage.value, page_size: pageSize.value },
    })
    tableData.value = Array.isArray(data.data) ? data.data : []
    total.value = typeof data.total === 'number' ? data.total : 0
    // 如果当前页超出范围，修正到第一页
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = 1
      const { data: newData } = await axios.get('/api/score-lines', {
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

const exportData = async () => {
  try {
    const params = { ...currentParams, format: 'csv' }
    const queryString = new URLSearchParams(params).toString()
    const url = `/api/export/score-lines?${queryString}`
    window.open(url, '_blank')
    ElMessage.success('正在导出数据...')
  } catch (e) {
    ElMessage.error('导出失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => fetchData())
defineExpose({ fetchData })
</script>

<style scoped>
.score-lines-table {
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

.score-high {
  color: #f56c6c;
  font-weight: 600;
}

.score-mid {
  color: #e6a23c;
  font-weight: 500;
}

.score-low {
  color: #67c23a;
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
</style>
