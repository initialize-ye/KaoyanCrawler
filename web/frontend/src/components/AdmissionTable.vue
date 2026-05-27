<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>录取数据</span>
        <el-tag type="info">共 {{ total }} 条</el-tag>
      </div>
    </template>

    <el-table
      :data="tableData"
      stripe
      border
      style="width: 100%"
      v-loading="loading"
      max-height="500"
    >
      <el-table-column prop="university" label="学校" width="150" fixed />
      <el-table-column prop="year" label="年份" width="80" align="center" />
      <el-table-column prop="list_type" label="类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.list_type === '录取名单' ? 'success' : 'warning'" size="small">
            {{ row.list_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="major" label="专业" width="200" show-overflow-tooltip />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="exam_id" label="考生编号" width="150" />
      <el-table-column prop="initial_score" label="初试成绩" width="100" align="center">
        <template #default="{ row }">
          {{ row.initial_score ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="retest_score" label="复试成绩" width="100" align="center">
        <template #default="{ row }">
          {{ row.retest_score ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="total_score" label="总分" width="100" align="center">
        <template #default="{ row }">
          {{ row.total_score ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="admission_status" label="状态" width="100" />
      <el-table-column prop="admission_type" label="录取类别" width="100" />
    </el-table>

    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="onPageChange"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)

let currentParams = {}

const fetchData = async (params = {}) => {
  loading.value = true
  currentParams = params

  try {
    const { data } = await axios.get('/api/admissions', {
      params: {
        ...params,
        page: currentPage.value,
        page_size: pageSize.value,
      },
    })
    tableData.value = data.data
    total.value = data.total
  } catch (e) {
    console.error('获取数据失败:', e)
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
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
