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
            <span class="material-icons group-arrow" :class="{ 'is-collapsed': group.collapsed }">expand_more</span>
            <span class="group-title">{{ group.university }}</span>
            <span class="tag-chip">{{ group.year }}年</span>
            <span class="tag-chip tag-chip--blue">{{ group.records.length }} 条</span>
          </div>
          <button class="text-btn text-btn--danger" @click.stop="deleteGroup(group)">删除全部</button>
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
  gap: var(--google-space-4);
  font-family: var(--google-font-roboto);
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.table-header__left {
  display: flex;
  align-items: center;
  gap: var(--google-space-3);
}

.table-header__title {
  font-family: var(--google-font);
  font-size: 16px;
  font-weight: 600;
  color: var(--google-text-primary);
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: var(--google-space-3);
}

.group-item {
  border: 1px solid var(--google-gray-200);
  border-radius: var(--google-radius-md);
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--google-space-3) var(--google-space-4);
  background: var(--google-gray-50);
  cursor: pointer;
  transition: background-color var(--google-transition-fast);
}

.group-header:hover {
  background: var(--google-gray-100);
}

.group-header__left {
  display: flex;
  align-items: center;
  gap: var(--google-space-3);
}

.group-arrow {
  transition: transform var(--google-transition-fast);
  color: var(--google-text-secondary);
}

.group-arrow.is-collapsed {
  transform: rotate(-90deg);
}

.group-title {
  font-family: var(--google-font);
  font-size: 15px;
  font-weight: 600;
  color: var(--google-text-primary);
}

.group-body {
  padding: var(--google-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--google-space-3);
}

.empty-tip {
  padding: 40px 0;
}

.rule-item {
  border: 1px solid var(--google-gray-200);
  border-radius: var(--google-radius-md);
  overflow: hidden;
}

.rule-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--google-space-3) var(--google-space-4);
  background: var(--google-gray-50);
  border-bottom: 1px solid var(--google-gray-200);
}

.rule-item__title {
  font-family: var(--google-font);
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: var(--google-text-primary);
  flex: 1;
}

.rule-item__meta {
  font-size: 12px;
  color: var(--google-text-secondary);
  margin-right: var(--google-space-3);
}

.rule-item__delete {
  flex-shrink: 0;
}

.rule-item__body {
  padding: var(--google-space-3) var(--google-space-4);
}

.rule-item__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--google-space-3);
}

.rule-item__section {
  margin-bottom: var(--google-space-3);
}

.rule-item__label {
  font-family: var(--google-font);
  font-size: 12px;
  font-weight: 600;
  color: var(--google-blue);
  background: var(--google-blue-bg);
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: var(--google-space-1);
}

.rule-item__text {
  font-size: 13px;
  color: var(--google-text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.rule-item__source {
  font-size: 12px;
  color: var(--google-text-secondary);
  margin-top: var(--google-space-2);
  padding-top: var(--google-space-2);
  border-top: 1px solid var(--google-gray-200);
}

.rule-item__source a {
  color: var(--google-blue);
  text-decoration: none;
}

.rule-item__source a:hover {
  text-decoration: underline;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: var(--google-space-2);
}

@media (max-width: 768px) {
  .group-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--google-space-2);
  }

  .rule-item__header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--google-space-2);
  }

  .rule-item__row {
    grid-template-columns: 1fr;
  }

  .table-pagination {
    justify-content: center;
  }
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
.text-btn--danger { color: var(--google-red); }
.text-btn--danger:hover { background: #fce8e6; }
</style>
