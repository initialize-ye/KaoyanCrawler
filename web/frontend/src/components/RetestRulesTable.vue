<template>
  <div class="rules-table">
    <div class="table-header">
      <div class="table-header__left">
        <span class="table-header__title">复试细则</span>
        <el-tag type="info" size="small">{{ total }}</el-tag>
      </div>
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
          <div v-for="(rule, i) in group.records" :key="i" class="rule-item">
            <div class="rule-item__header">
              <h4 class="rule-item__title">{{ rule.title }}</h4>
              <div class="rule-item__meta">
                <span v-if="rule.department">{{ rule.department }}</span>
                <span v-if="rule.major"> · {{ rule.major }}</span>
              </div>
              <el-button type="danger" size="small" text class="rule-item__delete" @click="deleteRow(rule)">
                删除
              </el-button>
            </div>
            <div class="rule-item__body">
              <div class="rule-item__section" v-if="rule.content_summary">
                <div class="rule-item__label">内容摘要</div>
                <div class="rule-item__text">{{ rule.content_summary }}</div>
              </div>
              <div class="rule-item__row">
                <div class="rule-item__section" v-if="rule.retest_format">
                  <div class="rule-item__label">复试形式</div>
                  <div class="rule-item__text">{{ rule.retest_format }}</div>
                </div>
                <div class="rule-item__section" v-if="rule.score_composition">
                  <div class="rule-item__label">成绩构成</div>
                  <div class="rule-item__text">{{ rule.score_composition }}</div>
                </div>
              </div>
              <div class="rule-item__section" v-if="rule.retest_content">
                <div class="rule-item__label">复试内容</div>
                <div class="rule-item__text">{{ rule.retest_content }}</div>
              </div>
              <div class="rule-item__section" v-if="rule.other_requirements">
                <div class="rule-item__label">其他要求</div>
                <div class="rule-item__text">{{ rule.other_requirements }}</div>
              </div>
              <div class="rule-item__source" v-if="rule.source_url">
                来源: <a :href="rule.source_url" target="_blank" rel="noopener">{{ rule.source_url }}</a>
              </div>
            </div>
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
    const { data } = await axios.get('/api/retest-rules', {
      params: { ...params, page: currentPage.value, page_size: pageSize.value },
    })
    tableData.value = Array.isArray(data.data) ? data.data : []
    total.value = typeof data.total === 'number' ? data.total : 0
    updateGroupedData()
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = 1
      const { data: newData } = await axios.get('/api/retest-rules', {
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
    await ElMessageBox.confirm(`确定删除 ${row.title}？`, '确认删除', {
      type: 'warning',
    })
    await axios.delete(`/api/retest-rules/${row.id}`)
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

onMounted(() => fetchData())
defineExpose({ fetchData })
</script>

<style scoped>
.rules-table {
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
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-tip {
  padding: 40px 0;
}

.rule-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}

.rule-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.rule-item__title {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
  flex: 1;
}

.rule-item__meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-right: 12px;
}

.rule-item__delete {
  flex-shrink: 0;
}

.rule-item__body {
  padding: 12px 16px;
}

.rule-item__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.rule-item__section {
  margin-bottom: 12px;
}

.rule-item__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
}

.rule-item__text {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  white-space: pre-wrap;
}

.rule-item__source {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.rule-item__source a {
  color: var(--el-color-primary);
  text-decoration: none;
}

.rule-item__source a:hover {
  text-decoration: underline;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

@media (max-width: 768px) {
  .group-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .rule-item__header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .rule-item__row {
    grid-template-columns: 1fr;
  }

  .table-pagination {
    justify-content: center;
  }
}
</style>
