<template>
  <div class="subject-table">
    <div class="table-header">
      <div class="table-header__left">
        <span class="table-header__title">招生专业目录</span>
        <el-tag type="info" size="small">{{ total }}</el-tag>
      </div>
    </div>

    <!-- 按学校分组显示 -->
    <div v-if="groupedData.length" class="group-list" role="list">
      <div v-for="group in groupedData" :key="group.university" class="group-item" role="listitem">
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
              <el-table-column prop="department" label="学院" min-width="140" show-overflow-tooltip />
              <el-table-column prop="major_code" label="专业代码" width="100" />
              <el-table-column prop="major_name" label="专业名称" min-width="150" show-overflow-tooltip />
              <el-table-column prop="enrollment" label="招生人数" width="80" align="center">
                <template #default="{ row }">
                  <span v-if="row.enrollment">{{ row.enrollment }}</span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="research_direction" label="研究方向" min-width="120" show-overflow-tooltip />
              <el-table-column prop="subject1" label="政治" min-width="120" show-overflow-tooltip />
              <el-table-column prop="subject2" label="外语" min-width="120" show-overflow-tooltip />
              <el-table-column prop="subject3" label="业务课一" min-width="140" show-overflow-tooltip />
              <el-table-column prop="subject4" label="业务课二" min-width="140" show-overflow-tooltip />
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
      <el-empty description="暂无数据，点击右上角开始采集" />
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
import { ArrowDown } from '@element-plus/icons-vue'
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
    const { data } = await axios.get('/api/subjects', {
      params: { ...params, page: currentPage.value, page_size: pageSize.value },
    })
    tableData.value = Array.isArray(data.data) ? data.data : []
    total.value = typeof data.total === 'number' ? data.total : 0
    updateGroupedData()
    // 如果当前页超出范围，修正到第一页
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = 1
      // 重新获取第一页数据
      const { data: newData } = await axios.get('/api/subjects', {
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
    await ElMessageBox.confirm(`确定删除 ${row.major_name} (${row.major_code})？`, '确认删除', {
      type: 'warning',
    })
    await axios.delete(`/api/subjects/${row.id}`)
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
      `确定删除 ${group.university} ${group.year}年的全部数据（招生目录、录取名单、分数线）？`,
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

onMounted(() => fetchData())
defineExpose({ fetchData })
</script>

<style scoped>
.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.table-header__left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.table-header__title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.group-item {
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--color-blue-500);
  border-radius: var(--radius-lg);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--surface-tinted);
  cursor: pointer;
  user-select: none;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.group-header:hover {
  background: var(--el-fill-color-light);
}

.group-header:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: -2px;
}

.group-header__left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.group-arrow {
  transition: transform 0.2s;
}

.group-arrow.is-collapsed {
  transform: rotate(-90deg);
}

.group-title {
  font-weight: 600;
  font-size: var(--font-size-base);
}

.group-body {
  padding: var(--space-3);
}

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.empty-tip {
  padding: 40px 0;
}

.table-pagination {
  margin-top: var(--space-4);
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .table-pagination {
    justify-content: center;
  }
}
</style>
