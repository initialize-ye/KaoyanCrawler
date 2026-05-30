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

    <!-- 按学校分组显示 -->
    <div v-if="groupedData.length" class="group-list" role="list">
      <div v-for="group in groupedData" :key="group.key" class="group-item" role="listitem">
        <div class="group-header" @click="toggleCollapse(group)" @keydown.enter="toggleCollapse(group)"
          @keydown.space.prevent="toggleCollapse(group)" tabindex="0"
          :aria-expanded="!group.collapsed" :aria-label="`${group.university} ${group.year}年 ${group.records.length}条`">
          <div class="group-header__left">
            <el-icon class="group-arrow" :class="{ 'is-collapsed': group.collapsed }"><ArrowDown /></el-icon>
            <span class="group-title">{{ group.university }}</span>
            <el-tag size="small" type="info">{{ group.year }}年</el-tag>
            <el-tag size="small">{{ group.records.length }} 条</el-tag>
          </div>
          <el-button type="danger" size="small" text @click.stop="deleteGroup(group)">
            删除全部
          </el-button>
        </div>
        <div v-show="!group.collapsed" class="group-body" role="region">
          <div class="table-scroll">
            <el-table :data="group.records" stripe border size="small" style="width: 100%"
              :max-height="350" empty-text="暂无数据">
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
              <el-table-column prop="score1" label="单科1" width="70" align="center">
                <template #default="{ row }">
                  <span>{{ row.score1 ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="score2" label="单科2" width="70" align="center">
                <template #default="{ row }">
                  <span>{{ row.score2 ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-button type="danger" size="small" text @click="deleteRow(row)">
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="empty-tip">
      <el-empty description="暂无数据" />
    </div>

    <div class="table-pagination" v-if="total > pageSize">
      <el-pagination v-model:current-page="currentPage" :page-size="pageSize" :total="total"
        :layout="isMobile ? 'prev, pager, next' : 'total, prev, pager, next, jumper'"
        :small="isMobile" @current-change="onPageChange" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, ArrowDown } from '@element-plus/icons-vue'
import { useResponsive } from '../composables/useResponsive'

const { isMobile } = useResponsive()

const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const groupedData = ref([])
const collapsedMap = ref({})

let currentParams = {}

const scoreClass = (score) => {
  if (score == null) return ''
  if (score >= 350) return 'score-high'
  if (score >= 300) return 'score-mid'
  return 'score-low'
}

// 按学校和年份分组
const updateGroupedData = () => {
  const groups = {}
  for (const row of tableData.value) {
    const key = `${row.university}_${row.year}`
    if (!groups[key]) {
      groups[key] = {
        university: row.university,
        year: row.year,
        records: [],
      }
    }
    groups[key].records.push(row)
  }
  groupedData.value = Object.entries(groups).map(([key, group]) => ({
    ...group,
    key,
    collapsed: collapsedMap.value[key] ?? false,
  }))
}

const toggleCollapse = (group) => {
  group.collapsed = !group.collapsed
  collapsedMap.value[group.key] = group.collapsed
}

const fetchData = async (params = {}) => {
  loading.value = true
  currentParams = params
  try {
    const { data } = await axios.get('/api/score-lines', {
      params: { ...params, page: currentPage.value, page_size: pageSize.value },
    })
    tableData.value = Array.isArray(data.data) ? data.data : []
    total.value = typeof data.total === 'number' ? data.total : 0
    updateGroupedData()
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = 1
      const { data: newData } = await axios.get('/api/score-lines', {
        params: { ...params, page: 1, page_size: pageSize.value },
      })
      tableData.value = Array.isArray(newData.data) ? newData.data : []
      total.value = typeof newData.total === 'number' ? newData.total : 0
      updateGroupedData()
    }
  } catch (e) {
    tableData.value = []
    total.value = 0
    groupedData.value = []
    ElMessage.error('获取数据失败: ' + (e.response?.data?.detail || e.message || '网络错误'))
  } finally {
    loading.value = false
  }
}

const onPageChange = (page) => {
  currentPage.value = page
  fetchData(currentParams)
}

const deleteRow = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除 ${row.discipline} (${row.category})？`, '确认删除', {
      type: 'warning',
    })
    await axios.delete(`/api/score-lines/${row.id}`)
    ElMessage.success('已删除')
    fetchData(currentParams)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

const deleteGroup = async (group) => {
  try {
    await ElMessageBox.confirm(
      `确定删除 ${group.university} ${group.year}年的全部 ${group.records.length} 条记录？`,
      '确认删除',
      { type: 'warning' }
    )
    // 按学校+年份删除所有数据
    const { data } = await axios.post('/api/delete-all-by-school', {
      university: group.university,
      year: group.year,
    })
    ElMessage.success(data.message || '已删除')
    fetchData(currentParams)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
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

.group-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  cursor: pointer;
  transition: background-color 0.2s;
}

.group-header:hover {
  background: var(--el-fill-color-light);
}

.group-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.group-arrow {
  transition: transform 0.2s;
}

.group-arrow.is-collapsed {
  transform: rotate(-90deg);
}

.group-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.group-body {
  padding: 12px;
}

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

.empty-tip {
  padding: 40px 0;
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

  .group-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .table-pagination {
    justify-content: center;
  }
}
</style>
