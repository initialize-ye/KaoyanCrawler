<template>
  <el-dialog v-model="visible" title="添加学校配置" width="900px" :close-on-click-modal="false">
    <el-steps :active="step" finish-status="success" align-center>
      <el-step title="输入学校信息" />
      <el-step title="发现目标页面" />
      <el-step title="选择表格" />
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
          <el-form-item label="研究生院URL" required>
            <el-input v-model="form.url" placeholder="如：https://yz.tsinghua.edu.cn" />
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤2：自动发现链接 -->
      <div v-if="step === 1">
        <div v-loading="discovering" style="margin-top: 20px">
          <p style="margin-bottom: 16px; color: #606266">
            正在扫描 <strong>{{ form.url }}</strong> 页面，查找复试/录取名单链接...
          </p>

          <div v-if="discoveredLinks.admission_list?.length">
            <h4>录取名单相关链接：</h4>
            <el-radio-group v-model="selectedAdmissionLink" style="display: flex; flex-direction: column; gap: 8px; margin: 12px 0">
              <el-radio v-for="(link, i) in discoveredLinks.admission_list" :key="i" :value="link.url" border>
                {{ link.text }}
                <el-tag size="small" type="info" style="margin-left: 8px">{{ link.url }}</el-tag>
              </el-radio>
            </el-radio-group>
          </div>

          <div v-if="discoveredLinks.program_catalog?.length">
            <h4>招生专业目录链接：</h4>
            <el-radio-group v-model="selectedCatalogLink" style="display: flex; flex-direction: column; gap: 8px; margin: 12px 0">
              <el-radio v-for="(link, i) in discoveredLinks.program_catalog" :key="i" :value="link.url" border>
                {{ link.text }}
                <el-tag size="small" type="info" style="margin-left: 8px">{{ link.url }}</el-tag>
              </el-radio>
            </el-radio-group>
          </div>

          <el-empty v-if="!discovering && !hasAnyLink" description="未发现相关链接，请检查URL是否正确" />

          <el-divider />
          <p style="color: #909399; font-size: 13px">
            没找到？也可以手动输入目标页面URL：
          </p>
          <el-input v-model="manualUrl" placeholder="手动输入目标页面URL" style="margin-top: 8px">
            <template #append>
              <el-button @click="addManualLink">添加</el-button>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 步骤3：选择表格 -->
      <div v-if="step === 2">
        <div v-loading="previewing" style="margin-top: 20px">
          <p style="margin-bottom: 16px; color: #606266">
            页面 <strong>{{ currentPreviewUrl }}</strong> 中发现以下表格，请选择要爬取的表格：
          </p>

          <div v-for="table in previewTables" :key="table.index" class="table-preview-card"
               :class="{ selected: selectedTableIndex === table.index }"
               @click="selectTable(table)">
            <div class="table-header">
              <el-tag>表格 {{ table.index + 1 }}</el-tag>
              <span style="margin-left: 8px">{{ table.row_count }} 行数据</span>
              <el-tag v-if="selectedTableIndex === table.index" type="success" style="margin-left: auto">已选择</el-tag>
            </div>

            <el-table :data="table.sample_rows" border size="small" style="margin-top: 8px">
              <el-table-column v-for="(header, hi) in table.headers" :key="hi" :label="header" min-width="100">
                <template #default="{ row }">
                  {{ row[hi] || '-' }}
                </template>
              </el-table-column>
            </el-table>

            <p style="margin-top: 4px; font-size: 12px; color: #909399">
              CSS选择器: <code>{{ table.selector }}</code>
            </p>
          </div>

          <el-empty v-if="!previewing && previewTables.length === 0" description="页面中未发现表格" />
        </div>

        <el-divider />
        <h4>列映射配置</h4>
        <p style="color: #909399; font-size: 13px; margin-bottom: 12px">
          将表格的每一列映射到对应的字段（点击表头可修改）：
        </p>
        <el-table :data="columnMapping" border size="small">
          <el-table-column prop="index" label="列序号" width="80" />
          <el-table-column prop="header" label="表头名称" width="150" />
          <el-table-column label="映射字段">
            <template #default="{ row }">
              <el-select v-model="row.field" placeholder="选择字段" clearable>
                <el-option label="考生编号" value="exam_id" />
                <el-option label="姓名" value="name" />
                <el-option label="专业" value="major" />
                <el-option label="初试成绩" value="initial_score" />
                <el-option label="复试成绩" value="retest_score" />
                <el-option label="总分" value="total_score" />
                <el-option label="录取状态" value="admission_status" />
                <el-option label="录取类别" value="admission_type" />
                <el-option label="学习方式" value="study_mode" />
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

      <!-- 步骤4：确认生成 -->
      <div v-if="step === 3">
        <el-descriptions title="配置预览" :column="1" border style="margin-top: 20px">
          <el-descriptions-item label="学校名称">{{ form.name }}</el-descriptions-item>
          <el-descriptions-item label="学校代码">{{ form.code }}</el-descriptions-item>
          <el-descriptions-item label="研究生院URL">{{ form.url }}</el-descriptions-item>
          <el-descriptions-item label="目标数量">{{ targets.length }} 个</el-descriptions-item>
        </el-descriptions>

        <div v-for="(target, i) in targets" :key="i" style="margin-top: 16px">
          <el-card shadow="never">
            <template #header>{{ target.name }}</template>
            <p>URL: {{ target.url }}</p>
            <p>格式: {{ target.format }}</p>
            <p>类型: {{ target.type === 'admission_list' ? '录取名单' : '招生专业目录' }}</p>
            <p v-if="target.selector">选择器: {{ target.selector }}</p>
          </el-card>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button v-if="step > 0" @click="step--">上一步</el-button>
      <el-button v-if="step < 3" type="primary" @click="nextStep" :disabled="!canProceed">
        {{ step === 2 ? '生成配置' : '下一步' }}
      </el-button>
      <el-button v-if="step === 3" type="success" @click="saveConfig" :loading="saving">
        保存配置
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 常见985/211院校名称 -> 拼音代码映射
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
  // 优先从映射表查找
  if (UNIVERSITY_CODE_MAP[name]) return UNIVERSITY_CODE_MAP[name]
  // 简单处理：去掉"大学"等后缀，用名称前两个字的unicode作为临时code
  return name.replace(/大学|学院|学校/g, '').slice(0, 4) || 'unknown'
}

const visible = ref(false)
const step = ref(0)
const discovering = ref(false)
const previewing = ref(false)
const saving = ref(false)

const form = ref({ name: '', code: '', url: '' })

// 监听学校名称变化，自动生成代码
watch(() => form.value.name, (newName) => {
  if (newName) form.value.code = generateCode(newName)
})
const discoveredLinks = ref({})
const selectedAdmissionLink = ref('')
const selectedCatalogLink = ref('')
const manualUrl = ref('')

const previewTables = ref([])
const currentPreviewUrl = ref('')
const selectedTableIndex = ref(-1)
const columnMapping = ref([])

const targets = ref([])

const hasAnyLink = computed(() => {
  return (discoveredLinks.value.admission_list?.length || 0) +
         (discoveredLinks.value.program_catalog?.length || 0) > 0
})

const canProceed = computed(() => {
  if (step.value === 0) return form.value.name && form.value.url
  if (step.value === 1) return selectedAdmissionLink.value || selectedCatalogLink.value || targets.value.length > 0
  if (step.value === 2) return selectedTableIndex.value >= 0
  return true
})

const open = () => {
  visible.value = true
  step.value = 0
  form.value = { name: '', code: '', url: '' }
  discoveredLinks.value = {}
  selectedAdmissionLink.value = ''
  selectedCatalogLink.value = ''
  targets.value = []
  previewTables.value = []
  selectedTableIndex.value = -1
  columnMapping.value = []
}

const nextStep = async () => {
  if (step.value === 0) {
    // 步骤1 -> 2：发现链接
    discovering.value = true
    try {
      const { data } = await axios.get('/api/discover', { params: { url: form.value.url } })
      discoveredLinks.value = data
    } catch (e) {
      ElMessage.error('发现链接失败: ' + e.message)
    }
    discovering.value = false
  }

  if (step.value === 1) {
    // 步骤2 -> 3：预览表格
    const url = selectedAdmissionLink.value || selectedCatalogLink.value
    if (!url) {
      ElMessage.warning('请选择一个目标链接')
      return
    }
    await loadTablePreview(url)
  }

  if (step.value === 2) {
    // 步骤3 -> 4：生成配置目标
    buildTargets()
  }

  step.value++
}

const loadTablePreview = async (url) => {
  previewing.value = true
  currentPreviewUrl.value = url
  selectedTableIndex.value = -1
  try {
    const { data } = await axios.get('/api/preview-tables', { params: { url } })
    previewTables.value = data.tables || []
    if (previewTables.value.length === 1) {
      selectTable(previewTables.value[0])
    }
  } catch (e) {
    ElMessage.error('预览表格失败: ' + e.message)
  }
  previewing.value = false
}

const selectTable = (table) => {
  selectedTableIndex.value = table.index
  columnMapping.value = table.headers.map((header, i) => ({
    index: i,
    header,
    field: guessField(header),
  }))
}

const guessField = (header) => {
  const mapping = {
    '考生编号': 'exam_id', '准考证号': 'exam_id', '报名号': 'exam_id',
    '姓名': 'name', '名字': 'name',
    '专业': 'major', '报考专业': 'major', '录取专业': 'major',
    '初试成绩': 'initial_score', '初试总分': 'initial_score', '初试': 'initial_score',
    '复试成绩': 'retest_score', '复试总分': 'retest_score', '复试': 'retest_score',
    '总分': 'total_score', '总成绩': 'total_score',
    '录取状态': 'admission_status', '状态': 'admission_status', '是否录取': 'admission_status',
    '录取类别': 'admission_type', '类别': 'admission_type',
    '学习方式': 'study_mode', '全日制': 'study_mode',
    '专业代码': 'major_code', '代码': 'major_code',
    '科目一': 'subject1', '政治': 'subject1',
    '科目二': 'subject2', '外语': 'subject2', '英语': 'subject2',
    '科目三': 'subject3', '业务课一': 'subject3',
    '科目四': 'subject4', '业务课二': 'subject4',
  }
  for (const [key, value] of Object.entries(mapping)) {
    if (header.includes(key)) return value
  }
  return ''
}

const buildTargets = () => {
  targets.value = []

  if (selectedAdmissionLink.value) {
    const columns = {}
    for (const col of columnMapping.value) {
      if (col.field) columns[col.index] = col.field
    }
    targets.value.push({
      name: `${new Date().getFullYear()}年硕士研究生录取名单`,
      type: 'admission_list',
      url: selectedAdmissionLink.value,
      format: 'html',
      selectors: { table: 'table', row: 'tr', columns },
      parse_rules: { year: new Date().getFullYear(), list_type: '录取名单' },
      selector: previewTables.value[selectedTableIndex.value]?.selector,
    })
  }

  if (selectedCatalogLink.value) {
    targets.value.push({
      name: `${new Date().getFullYear()}年硕士研究生招生专业目录`,
      type: 'program_catalog',
      url: selectedCatalogLink.value,
      format: 'html',
      selectors: { table: 'table', row: 'tr', columns: {} },
      parse_rules: { year: new Date().getFullYear() },
    })
  }
}

const addManualLink = () => {
  if (!manualUrl.value) return
  if (!discoveredLinks.value.admission_list) discoveredLinks.value.admission_list = []
  discoveredLinks.value.admission_list.push({
    url: manualUrl.value,
    text: '手动添加的链接',
    matched_keyword: 'manual',
  })
  selectedAdmissionLink.value = manualUrl.value
  manualUrl.value = ''
}

const saveConfig = async () => {
  saving.value = true
  try {
    await axios.post('/api/generate-config', {
      university_name: form.value.name,
      university_code: form.value.code,
      graduate_school_url: form.value.url,
      targets: targets.value,
    })
    ElMessage.success('配置保存成功！')
    visible.value = false
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  }
  saving.value = false
}

defineExpose({ open })
</script>

<style scoped>
.step-content {
  min-height: 300px;
  padding: 0 20px;
}

.table-preview-card {
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
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
  margin-bottom: 8px;
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
</style>
