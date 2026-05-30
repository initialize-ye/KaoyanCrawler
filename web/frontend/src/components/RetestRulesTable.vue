<template>
  <div class="rules-table">
    <div class="table-header">
      <div class="table-header__left">
        <span class="table-header__title">复试细则</span>
        <el-tag type="info" size="small">{{ total }}</el-tag>
      </div>
    </div>

    <div v-if="!tableData.length && !loading" class="empty-tip">
      <el-empty description="暂无数据" />
    </div>

    <div v-else class="rules-list">
      <div v-for="(rule, i) in tableData" :key="i" class="rule-item">
        <div class="rule-item__header">
          <h4 class="rule-item__title">{{ rule.title }}</h4>
          <div class="rule-item__meta">
            <span>{{ rule.university }}</span>
            <span v-if="rule.department"> · {{ rule.department }}</span>
            <span v-if="rule.major"> · {{ rule.major }}</span>
            <span> · {{ rule.year }}年</span>
          </div>
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
import { ElMessage } from 'element-plus'
import { useResponsive } from '../composables/useResponsive'

const { isMobile } = useResponsive()

const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

let currentParams = {}

const fetchData = async (params = {}) => {
  loading.value = true
  currentParams = params
  try {
    const { data } = await axios.get('/api/retest-rules', {
      params: { ...params, page: currentPage.value, page_size: pageSize.value },
    })
    tableData.value = Array.isArray(data.data) ? data.data : []
    total.value = typeof data.total === 'number' ? data.total : 0
    // 如果当前页超出范围，修正到第一页
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = 1
      // 重新获取第一页数据
      const { data: newData } = await axios.get('/api/retest-rules', {
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

.empty-tip {
  padding: 40px 0;
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.rule-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.rule-item__header {
  padding: var(--space-3) var(--space-4);
  background: var(--surface-tinted);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.rule-item__title {
  font-size: var(--font-size-base);
  font-weight: 600;
  margin: 0 0 var(--space-1) 0;
  color: var(--el-text-color-primary);
}

.rule-item__meta {
  font-size: var(--font-size-xs);
  color: var(--el-text-color-secondary);
}

.rule-item__body {
  padding: var(--space-3) var(--space-4);
}

.rule-item__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.rule-item__section {
  margin-bottom: var(--space-3);
}

.rule-item__label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-blue-700);
  background: var(--color-blue-50);
  display: inline-block;
  padding: 1px var(--space-2);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-1);
}

.rule-item__text {
  font-size: var(--font-size-sm);
  color: var(--el-text-color-regular);
  line-height: 1.6;
  white-space: pre-wrap;
}

.rule-item__source {
  font-size: var(--font-size-xs);
  color: var(--el-text-color-secondary);
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--el-border-color-lighter);
}

.rule-item__source a {
  color: var(--color-blue-600);
  text-decoration: none;
}

.rule-item__source a:hover {
  text-decoration: underline;
}

.table-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .rule-item__row {
    grid-template-columns: 1fr;
  }

  .table-pagination {
    justify-content: center;
  }
}
</style>
