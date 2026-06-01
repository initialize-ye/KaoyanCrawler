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
            <span class="material-icons group-arrow" :class="{ 'is-collapsed': group.collapsed }">expand_more</span>
            <span class="group-title">{{ group.university }}</span>
            <span class="tag-chip">{{ group.year }}年</span>
            <span class="tag-chip tag-chip--blue">{{ group.records.length }} 条</span>
          </div>
          <button class="text-btn text-btn--danger" @click.stop="deleteGroup(group)">删除全部</button>
        </div>
        <div v-show="!group.collapsed" class="group-body" role="region">
          <div class="table-scroll">
            <el-table :data="group.records" stripe border size="small" style="width: 100%"
              :max-height="500" empty-text="暂无数据">
              <el-table-column prop="department" label="学院" min-width="140" show-overflow-tooltip />
              <el-table-column prop="major_code" label="专业代码" width="100" />
              <el-table-column prop="major_name" label="专业名称" min-width="150" show-overflow-tooltip />
              <el-table-column prop="enrollment" label="招生人数" width="80" align="center">
                <template #default="{ row }">
                  <span v-if="row.enrollment">{{ row.enrollment }}</span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="retest_score_line" label="复试线" width="80" align="center">
                <template #default="{ row }">
                  <span v-if="row.retest_score_line" class="score-highlight">{{ row.retest_score_line }}</span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="retest_count" label="复试人数" width="80" align="center">
                <template #default="{ row }">
                  <span v-if="row.retest_count">{{ row.retest_count }}</span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="admission_count" label="录取人数" width="80" align="center">
                <template #default="{ row }">
                  <span v-if="row.admission_count">{{ row.admission_count }}</span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="admission_ratio" label="复录比" width="70" align="center">
                <template #default="{ row }">
                  <span v-if="row.admission_ratio">{{ row.admission_ratio }}</span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column label="录取分数" align="center">
                <el-table-column prop="admission_min_score" label="最低" width="65" align="center">
                  <template #default="{ row }">
                    <span v-if="row.admission_min_score">{{ row.admission_min_score }}</span>
                    <span v-else class="text-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="admission_avg_score" label="平均" width="65" align="center">
                  <template #default="{ row }">
                    <span v-if="row.admission_avg_score">{{ row.admission_avg_score }}</span>
                    <span v-else class="text-muted">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="admission_max_score" label="最高" width="65" align="center">
                  <template #default="{ row }">
                    <span v-if="row.admission_max_score">{{ row.admission_max_score }}</span>
                    <span v-else class="text-muted">-</span>
                  </template>
                </el-table-column>
              </el-table-column>
              <el-table-column prop="research_direction" label="研究方向" min-width="120" show-overflow-tooltip />
              <el-table-column prop="subject1" label="政治" min-width="120" show-overflow-tooltip />
              <el-table-column prop="subject2" label="外语" min-width="120" show-overflow-tooltip />
              <el-table-column prop="subject3" label="业务课一" min-width="140" show-overflow-tooltip />
              <el-table-column prop="subject4" label="业务课二" min-width="140" show-overflow-tooltip />
              <el-table-column prop="transfer_type" label="调剂" width="80" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.transfer_type" type="warning" size="small">{{ row.transfer_type }}</el-tag>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
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
  margin-bottom: var(--google-space-4);
}

.table-header__left {
  display: flex;
  align-items: center;
  gap: var(--google-space-3);
}

.table-header__title {
  font-family: var(--google-font);
  font-size: 16px;
  font-weight: 500;
  color: var(--google-text-primary);
}

.tag-chip {
  display: inline-block;
  padding: 2px 10px;
  background: var(--google-gray-100);
  color: var(--google-text-secondary);
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--google-radius-full);
}

.tag-chip--blue {
  background: var(--google-blue-bg);
  color: var(--google-blue);
}

.text-btn {
  border: none;
  background: transparent;
  font-family: var(--google-font);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: var(--google-radius-full);
  transition: all var(--google-transition-fast);
}

.text-btn--danger {
  color: var(--google-red);
}

.text-btn--danger:hover {
  background: #fce8e6;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: var(--google-space-4);
}

.group-item {
  background: var(--google-surface);
  border: 1px solid var(--google-gray-200);
  border-left: 3px solid var(--google-blue);
  border-radius: var(--google-radius-md);
  box-shadow: var(--google-elevation-1);
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--google-space-3) var(--google-space-4);
  background: var(--google-gray-50);
  cursor: pointer;
  user-select: none;
  transition: background var(--google-transition-fast);
}

.group-header:hover {
  background: var(--google-gray-100);
}

.group-header:focus-visible {
  outline: 2px solid var(--google-blue);
  outline-offset: -2px;
}

.group-header__left {
  display: flex;
  align-items: center;
  gap: var(--google-space-2);
}

.group-arrow {
  color: var(--google-text-tertiary);
  font-size: 20px;
  transition: transform var(--google-transition-fast);
}

.group-arrow.is-collapsed {
  transform: rotate(-90deg);
}

.group-title {
  font-family: var(--google-font);
  font-weight: 500;
  font-size: 14px;
  color: var(--google-text-primary);
}

.group-body {
  padding: var(--google-space-4);
}

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.empty-tip {
  padding: 60px 0;
  text-align: center;
  color: var(--google-text-tertiary);
}

.score-highlight {
  color: var(--google-red);
  font-weight: 600;
}

.text-muted {
  color: var(--google-text-tertiary);
}

.table-pagination {
  margin-top: var(--google-space-4);
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .table-pagination {
    justify-content: center;
  }
}
</style>
