<template>
  <el-dialog v-model="visible" title="添加学校配置" width="950px" :close-on-click-modal="false">
    <el-steps :active="step" finish-status="success" align-center>
      <el-step title="学校信息" />
      <el-step title="添加数据源" />
      <el-step title="确认生成" />
    </el-steps>

    <div class="step-content">
      <!-- 步骤1：输入学校基本信息 -->
      <div v-if="step === 0">
        <el-form :model="form" label-width="120px" style="margin-top: 20px">
          <el-form-item label="学校名称" required>
            <el-input v-model="form.name" placeholder="如：清华大学" />
          </el-form-item>
          <el-form-item label="学校代码">
            <el-input v-model="form.code" placeholder="自动生成，也可手动修改" />
            <div class="form-tip">用于配置文件名，输入学校名称后自动生成</div>
          </el-form-item>
          <el-form-item label="研究生院URL">
            <el-input v-model="form.url" placeholder="如：https://yz.tsinghua.edu.cn（可选）" />
            <div class="form-tip">如果名单在学院官网，此项可留空，直接在下一步添加</div>
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤2：管理多个数据源 -->
      <div v-if="step === 1">
        <!-- 已添加的数据源列表 -->
        <div style="margin-top: 20px">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
            <h4>已添加的数据源</h4>
            <el-button type="primary" size="small" @click="showAddSource = true">
              <el-icon><Plus /></el-icon> 添加数据源
            </el-button>
          </div>

          <el-empty v-if="sources.length === 0" description="还没有添加数据源，点击上方按钮添加" />

          <div v-for="(source, i) in sources" :key="i" class="source-card">
            <div class="source-header">
              <div>
                <el-tag :type="source.type === 'admission_list' ? 'success' : 'warning'" size="small">
                  {{ source.type === 'admission_list' ? '录取名单' : '招生目录' }}
                </el-tag>
                <span style="margin-left: 8px; font-weight: 500">{{ source.name || '未命名' }}</span>
              </div>
              <el-button type="danger" text size="small" @click="sources.splice(i, 1)">删除</el-button>
            </div>
            <div class="source-url">{{ source.url }}</div>
            <div v-if="source.tableSelector" class="source-detail">
              表格: <code>{{ source.tableSelector }}</code> | {{ source.columnCount }} 列
            </div>
          </div>
        </div>

        <!-- 添加数据源弹窗 -->
        <el-dialog v-model="showAddSource" title="添加数据源" width="800px" append-to-body>
          <el-form :model="newSource" label-width="100px">
            <el-form-item label="数据源名称">
              <el-input v-model="newSource.name" placeholder="如：计算机学院录取名单" />
            </el-form-item>
            <el-form-item label="类型">
              <el-radio-group v-model="newSource.type">
                <el-radio value="admission_list">复试/录取名单</el-radio>
                <el-radio value="program_catalog">招生专业目录</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="来源">
              <el-radio-group v-model="newSource.sourceType">
                <el-radio value="url">输入URL扫描</el-radio>
                <el-radio value="graduate">从研究生院发现</el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- 方式1：直接输入URL -->
            <el-form-item v-if="newSource.sourceType === 'url'" label="页面URL" required>
              <el-input v-model="newSource.url" placeholder="粘贴包含名单的页面URL">
                <template #append>
                  <el-button @click="scanUrl" :loading="scanning">扫描</el-button>
                </template>
              </el-input>
            </el-form-item>

            <!-- 方式2：从研究生院发现 -->
            <el-form-item v-if="newSource.sourceType === 'graduate'" label="研究生院">
              <el-button @click="discoverFromGrad" :loading="scanning" :disabled="!form.url">
                {{ form.url ? '扫描 ' + form.url : '请先在上一步填写研究生院URL' }}
              </el-button>
            </el-form-item>
          </el-form>

          <!-- 发现的链接列表 -->
          <div v-if="discoveredLinks.length" style="margin: 16px 0">
            <h4>发现的链接（点击选择）：</h4>
            <div class="link-list">
              <div v-for="(link, i) in discoveredLinks" :key="i" class="link-item"
                   :class="{ selected: newSource.url === link.url }"
                   @click="newSource.url = link.url; scanUrl()">
                <span>{{ link.text }}</span>
                <el-tag size="small" type="info">{{ link.url }}</el-tag>
              </div>
            </div>
          </div>

          <!-- 表格预览 -->
          <div v-if="previewTables.length" style="margin: 16px 0">
            <h4>选择要爬取的表格：</h4>
            <div v-for="table in previewTables" :key="table.index" class="table-preview-card"
                 :class="{ selected: selectedTableIndex === table.index }"
                 @click="selectTable(table)">
              <div class="table-header">
                <el-tag :type="table.type === 'table' ? '' : 'warning'">
                  {{ table.type === 'table' ? 'HTML表格' : table.type === 'div-table' ? 'DIV布局' : '文本表格' }}
                  {{ table.index + 1 }}
                </el-tag>
                <span style="margin-left: 8px">{{ table.row_count }} 行</span>
                <el-tag v-if="selectedTableIndex === table.index" type="success" style="margin-left: auto">已选择</el-tag>
              </div>
              <el-table :data="table.sample_rows" border size="small" style="margin-top: 8px" max-height="150">
                <el-table-column v-for="(header, hi) in table.headers" :key="hi" :label="header" min-width="80">
                  <template #default="{ row }">{{ row[hi] || '-' }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- 页面内容预览（当没有检测到表格时显示） -->
          <div v-if="!previewTables.length && pageInfo" style="margin: 16px 0">
            <el-alert type="warning" :closable="false" style="margin-bottom: 12px">
              <template #title>
                未检测到标准表格。以下是页面内容预览，请确认数据是否在此页面：
              </template>
            </el-alert>

            <el-card shadow="never" style="max-height: 300px; overflow-y: auto">
              <div v-if="pageInfo.title" style="font-weight: 600; margin-bottom: 8px">{{ pageInfo.title }}</div>
              <div v-for="(line, i) in pageInfo.sample_lines" :key="i" class="content-line">{{ line }}</div>
            </el-card>

            <!-- PDF下载链接 -->
            <div v-if="pageInfo.pdf_links?.length" style="margin-top: 12px">
              <h4>发现PDF链接：</h4>
              <div v-for="(pdf, i) in pageInfo.pdf_links" :key="i" class="link-item"
                   :class="{ selected: newSource.url === pdf.url }"
                   @click="newSource.url = pdf.url; newSource.format = 'pdf'">
                <span>{{ pdf.text }}</span>
                <el-tag size="small" type="warning">PDF</el-tag>
              </div>
            </div>

            <!-- 手动输入CSS选择器 -->
            <div style="margin-top: 12px">
              <el-input v-model="manualSelector" placeholder="手动输入CSS选择器（如 div.list tr）">
                <template #prepend>选择器</template>
                <template #append>
                  <el-button @click="applyManualSelector">应用</el-button>
                </template>
              </el-input>
            </div>
          </div>

          <!-- 列映射 -->
          <div v-if="columnMapping.length" style="margin: 16px 0">
            <h4>列映射（自动猜测，可手动调整）：</h4>
            <el-table :data="columnMapping" border size="small" max-height="200">
              <el-table-column prop="header" label="表头" width="120" />
              <el-table-column label="映射字段">
                <template #default="{ row }">
                  <el-select v-model="row.field" placeholder="选择" clearable size="small">
                    <el-option label="考生编号" value="exam_id" />
                    <el-option label="姓名" value="name" />
                    <el-option label="专业" value="major" />
                    <el-option label="初试成绩" value="initial_score" />
                    <el-option label="复试成绩" value="retest_score" />
                    <el-option label="总分" value="total_score" />
                    <el-option label="录取状态" value="admission_status" />
                    <el-option label="录取类别" value="admission_type" />
                    <el-option label="专业代码" value="major_code" />
                    <el-option label="专业名称" value="major_name" />
                    <el-option label="政治" value="subject1" />
                    <el-option label="外语" value="subject2" />
                    <el-option label="业务课一" value="subject3" />
                    <el-option label="业务课二" value="subject4" />
                  </el-select>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <template #footer>
            <el-button @click="showAddSource = false">取消</el-button>
            <el-button type="primary" @click="confirmAddSource" :disabled="!newSource.url || !newSource.type">
              添加
            </el-button>
          </template>
        </el-dialog>
      </div>

      <!-- 步骤3：确认生成 -->
      <div v-if="step === 2">
        <el-descriptions title="配置预览" :column="1" border style="margin-top: 20px">
          <el-descriptions-item label="学校名称">{{ form.name }}</el-descriptions-item>
          <el-descriptions-item label="学校代码">{{ form.code }}</el-descriptions-item>
          <el-descriptions-item label="研究生院URL">{{ form.url || '（未填写）' }}</el-descriptions-item>
          <el-descriptions-item label="数据源数量">{{ sources.length }} 个</el-descriptions-item>
        </el-descriptions>

        <div v-for="(source, i) in sources" :key="i" style="margin-top: 16px">
          <el-card shadow="never">
            <template #header>
              <div style="display: flex; align-items: center; gap: 8px">
                <el-tag :type="source.type === 'admission_list' ? 'success' : 'warning'" size="small">
                  {{ source.type === 'admission_list' ? '录取名单' : '招生目录' }}
                </el-tag>
                {{ source.name }}
              </div>
            </template>
            <p>URL: {{ source.url }}</p>
            <p v-if="source.tableSelector">选择器: {{ source.tableSelector }}</p>
          </el-card>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button v-if="step > 0" @click="step--">上一步</el-button>
      <el-button v-if="step < 2" type="primary" @click="nextStep" :disabled="!canProceed">
        {{ step === 1 && sources.length === 0 ? '跳过，直接生成' : '下一步' }}
      </el-button>
      <el-button v-if="step === 2" type="success" @click="saveConfig" :loading="saving">
        保存配置
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const UNIVERSITY_CODE_MAP = {
  '北京大学': 'pku', '清华大学': 'tsinghua', '中国人民大学': 'ruc',
  '北京航空航天大学': 'buaa', '北京理工大学': 'bit', '北京师范大学': 'bnu',
  '中央民族大学': 'muc', '中国农业大学': 'cau', '天津大学': 'tju',
  '南开大学': 'nankai', '大连理工大学': 'dlut', '东北大学': 'neu',
  '吉林大学': 'jlu', '哈尔滨工业大学': 'hit', '复旦大学': 'fudan',
  '上海交通大学': 'sjtu', '同济大学': 'tongji', '华东师范大学': 'ecnu',
  '南京大学': 'nju', '东南大学': 'seu', '浙江大学': 'zju',
  '中国科学技术大学': 'ustc', '厦门大学': 'xmu', '山东大学': 'sdu',
  '中国海洋大学': 'ouc', '武汉大学': 'whu', '华中科技大学': 'hust',
  '中南大学': 'csu', '湖南大学': 'hnu', '国防科技大学': 'nudt',
  '中山大学': 'sysu', '华南理工大学': 'scut', '四川大学': 'scu',
  '电子科技大学': 'uestc', '重庆大学': 'cqu', '西安交通大学': 'xjtu',
  '西北工业大学': 'nwpu', '兰州大学': 'lzu', '西北农林科技大学': 'nwafu',
}

const generateCode = (name) => {
  if (UNIVERSITY_CODE_MAP[name]) return UNIVERSITY_CODE_MAP[name]
  return name.replace(/大学|学院|学校/g, '').slice(0, 4) || 'unknown'
}

const visible = ref(false)
const step = ref(0)
const saving = ref(false)
const scanning = ref(false)
const showAddSource = ref(false)

const form = ref({ name: '', code: '', url: '' })
const sources = ref([])

// 新数据源表单
const newSource = ref({
  name: '',
  type: 'admission_list',
  sourceType: 'url',
  url: '',
  format: 'html',
})

const discoveredLinks = ref([])
const previewTables = ref([])
const selectedTableIndex = ref(-1)
const columnMapping = ref([])
const pageInfo = ref(null)
const manualSelector = ref('')

watch(() => form.value.name, (newName) => {
  if (newName) form.value.code = generateCode(newName)
})

const canProceed = computed(() => {
  if (step.value === 0) return form.value.name
  return true
})

const nextStep = () => {
  step.value++
}

// 扫描URL，预览表格
const scanUrl = async () => {
  if (!newSource.value.url) return
  scanning.value = true
  previewTables.value = []
  selectedTableIndex.value = -1
  columnMapping.value = []
  pageInfo.value = null

  try {
    const { data } = await axios.get('/api/preview-tables', { params: { url: newSource.value.url } })
    previewTables.value = data.tables || []
    pageInfo.value = data.page_info || null

    if (previewTables.value.length === 1) {
      selectTable(previewTables.value[0])
    }

    // 如果发现PDF链接，自动设置格式
    if (pageInfo.value?.pdf_links?.length && !previewTables.value.length) {
      newSource.value.format = 'pdf'
    }
  } catch (e) {
    ElMessage.error('扫描失败: ' + e.message)
  }
  scanning.value = false
}

// 应用手动CSS选择器
const applyManualSelector = () => {
  if (!manualSelector.value) return
  // 创建一个虚拟的表格配置
  previewTables.value = [{
    index: 0,
    type: 'manual',
    headers: ['列1', '列2', '列3', '列4', '列5'],
    row_count: 0,
    sample_rows: [],
    selector: manualSelector.value,
  }]
  selectTable(previewTables.value[0])
  ElMessage.success('已应用选择器: ' + manualSelector.value)
}

// 从研究生院发现链接
const discoverFromGrad = async () => {
  if (!form.value.url) return
  scanning.value = true
  discoveredLinks.value = []

  try {
    const { data } = await axios.get('/api/discover', { params: { url: form.value.url } })
    const key = newSource.value.type === 'admission_list' ? 'admission_list' : 'program_catalog'
    discoveredLinks.value = data[key] || []
    if (discoveredLinks.value.length === 0) {
      ElMessage.info('未发现相关链接，可以手动输入URL')
    }
  } catch (e) {
    ElMessage.error('发现失败: ' + e.message)
  }
  scanning.value = false
}

// 选择表格
const selectTable = (table) => {
  selectedTableIndex.value = table.index
  columnMapping.value = table.headers.map((header, i) => ({
    index: i,
    header,
    field: guessField(header),
  }))
}

// 猜测字段映射
const guessField = (header) => {
  const mapping = {
    '考生编号': 'exam_id', '准考证号': 'exam_id', '报名号': 'exam_id',
    '姓名': 'name',
    '专业': 'major', '报考专业': 'major', '录取专业': 'major',
    '初试成绩': 'initial_score', '初试总分': 'initial_score',
    '复试成绩': 'retest_score', '复试总分': 'retest_score',
    '总分': 'total_score', '总成绩': 'total_score',
    '录取状态': 'admission_status', '状态': 'admission_status',
    '录取类别': 'admission_type',
    '专业代码': 'major_code',
    '科目一': 'subject1', '政治': 'subject1',
    '科目二': 'subject2', '外语': 'subject2',
    '科目三': 'subject3', '业务课一': 'subject3',
    '科目四': 'subject4', '业务课二': 'subject4',
  }
  for (const [key, value] of Object.entries(mapping)) {
    if (header.includes(key)) return value
  }
  return ''
}

// 确认添加数据源
const confirmAddSource = () => {
  const columns = {}
  for (const col of columnMapping.value) {
    if (col.field) columns[col.index] = col.field
  }

  sources.value.push({
    name: newSource.value.name || `${form.value.name} ${newSource.value.type === 'admission_list' ? '录取名单' : '招生目录'}`,
    type: newSource.value.type,
    url: newSource.value.url,
    format: newSource.value.format || 'html',
    tableSelector: previewTables.value[selectedTableIndex.value]?.selector || '',
    columnCount: Object.keys(columns).length,
    columns,
  })

  // 重置
  showAddSource.value = false
  newSource.value = { name: '', type: 'admission_list', sourceType: 'url', url: '', format: 'html' }
  discoveredLinks.value = []
  previewTables.value = []
  selectedTableIndex.value = -1
  columnMapping.value = []
  pageInfo.value = null
  manualSelector.value = ''

  ElMessage.success('数据源已添加')
}

// 保存配置
const saveConfig = async () => {
  saving.value = true
  try {
    const targets = sources.value.map(s => ({
      name: s.name,
      type: s.type,
      url: s.url,
      format: s.format || 'html',
      selectors: {
        table: s.tableSelector || 'table',
        row: 'tr',
        columns: s.columns || {},
      },
      parse_rules: {
        year: new Date().getFullYear(),
        list_type: s.type === 'admission_list' ? '录取名单' : '招生目录',
      },
    }))

    await axios.post('/api/generate-config', {
      university_name: form.value.name,
      university_code: form.value.code,
      graduate_school_url: form.value.url || '',
      targets,
    })

    ElMessage.success('配置保存成功！')
    visible.value = false
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  }
  saving.value = false
}

const open = () => {
  visible.value = true
  step.value = 0
  form.value = { name: '', code: '', url: '' }
  sources.value = []
  showAddSource.value = false
  discoveredLinks.value = []
  previewTables.value = []
  selectedTableIndex.value = -1
  columnMapping.value = []
}

defineExpose({ open })
</script>

<style scoped>
.step-content {
  min-height: 300px;
  padding: 0 20px;
}

.source-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-url {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
  word-break: break-all;
}

.source-detail {
  font-size: 12px;
  color: #67c23a;
  margin-top: 4px;
}

.link-list {
  max-height: 200px;
  overflow-y: auto;
  margin-top: 8px;
}

.link-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.link-item:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.link-item.selected {
  border-color: #67c23a;
  background: #f0f9ff;
}

.table-preview-card {
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.table-preview-card:hover {
  border-color: #409eff;
}

.table-preview-card.selected {
  border-color: #67c23a;
  background-color: #f0f9ff;
}

.table-header {
  display: flex;
  align-items: center;
}

h4 {
  margin: 12px 0 8px;
  color: #303133;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.content-line {
  font-size: 13px;
  line-height: 1.8;
  color: #606266;
  border-bottom: 1px dashed #eee;
  padding: 2px 0;
}
</style>
