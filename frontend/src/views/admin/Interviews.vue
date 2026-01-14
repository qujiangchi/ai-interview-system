<template>
  <div>
    <div class="flex justify-between mb-4">
      <h2>Interviews</h2>
      <el-button type="primary" @click="handleAdd">Add Interview</el-button>
    </div>

    <el-table :data="interviews" border style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="interviewer" label="Interviewer" />
      <el-table-column prop="start_time" label="Start Time">
        <template #default="scope">
          {{ formatTime(scope.row.start_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status">
         <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="300">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">Edit</el-button>
          <el-button size="small" type="primary" @click="startInterview(scope.row.token)">Start Interview</el-button>
          <el-button size="small" type="info" @click="downloadReport(scope.row.id)" :disabled="scope.row.status < 3">Report</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? 'Edit Interview' : 'Add Interview'">
      <el-form :model="form" label-width="120px">
        <el-form-item label="Candidate">
           <el-select v-model="form.candidate_id" placeholder="Select Candidate">
            <el-option v-for="c in candidates" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Interviewer">
          <el-input v-model="form.interviewer" />
        </el-form-item>
        <el-form-item label="Start Time">
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="Select date and time" value-format="X" />
          <!-- Note: value-format="X" gives timestamp in seconds (string), we need to parse if needed or use number -->
        </el-form-item>
        <el-form-item label="Status">
          <el-select v-model="form.status">
            <el-option label="Not Started" :value="0" />
            <el-option label="Ready" :value="1" />
            <el-option label="In Progress" :value="2" />
            <el-option label="Completed" :value="3" />
            <el-option label="Report Generated" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="Passed">
           <el-switch v-model="form.is_passed" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleSubmit">Confirm</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

interface Interview {
  id: number
  candidate_id: number
  interviewer: string
  start_time: number
  status: number
  is_passed: number
  token: string
}

const interviews = ref<Interview[]>([])
const candidates = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const currentId = ref<number | null>(null)
const form = reactive({
  candidate_id: null as number | null,
  interviewer: '',
  start_time: '' as any, // timestamp
  status: 0,
  is_passed: 0
})

const fetchInterviews = async () => {
  loading.value = true
  try {
    const res = await request.get<any, Interview[]>('/admin/interviews')
    interviews.value = res
  } finally {
    loading.value = false
  }
}

const fetchCandidates = async () => {
    const res = await request.get<any, any[]>('/admin/candidates')
    candidates.value = res
}

const formatTime = (ts: number) => {
    return new Date(ts * 1000).toLocaleString()
}

const getStatusText = (status: number) => {
  const map: Record<number, string> = { 0: 'Not Started', 1: 'Ready', 2: 'In Progress', 3: 'Completed', 4: 'Report Generated' }
  return map[status] || 'Unknown'
}

const getStatusType = (status: number) => {
  const map: Record<number, string> = { 0: 'info', 1: 'primary', 2: 'warning', 3: 'success', 4: 'success' }
  return map[status] || ''
}

const handleAdd = () => {
  isEdit.value = false
  currentId.value = null
  Object.assign(form, {
      candidate_id: null,
      interviewer: '',
      start_time: Math.floor(Date.now() / 1000),
      status: 0,
      is_passed: 0
  })
  dialogVisible.value = true
}

const handleEdit = (row: Interview) => {
  isEdit.value = true
  currentId.value = row.id
  Object.assign(form, {
      candidate_id: row.candidate_id,
      interviewer: row.interviewer,
      start_time: row.start_time,
      status: row.status,
      is_passed: row.is_passed
  })
  dialogVisible.value = true
}

const handleStatusChange = async (row: Interview) => {
    try {
        await request.put(`/admin/interviews/${row.id}`, row)
        ElMessage.success('Status updated successfully')
    } catch (error) {
        // Revert status if failed (optional, but good UX)
        fetchInterviews()
    }
}

const handleDelete = (row: Interview) => {
  ElMessageBox.confirm('Are you sure to delete this interview?', 'Warning', {
    confirmButtonText: 'OK',
    cancelButtonText: 'Cancel',
    type: 'warning'
  }).then(async () => {
    await request.delete(`/admin/interviews/${row.id}`)
    ElMessage.success('Delete completed')
    fetchInterviews()
  })
}

const startInterview = (token: string) => {
    const url = `${window.location.origin}/interview/${token}`
    window.open(url, '_blank')
}

const downloadReport = (id: number) => {
    const token = localStorage.getItem('token')
    // Open in new tab for preview (browser handles pdf)
    // Add token to query param if needed, or rely on cookie if set?
    // Since we use header for auth, opening in new tab is tricky for protected routes.
    // However, we can use a temporary approach: 
    // 1. Fetch with blob as before, then open blob url in new tab.
    // 2. Or change API to allow query param token (less secure but common for downloads).
    
    // Let's stick to blob approach but open in new window for preview
    request.get(`/admin/interviews/${id}/report?preview=true`, { responseType: 'blob' }).then((res: any) => {
        const url = window.URL.createObjectURL(new Blob([res], { type: 'application/pdf' }))
        window.open(url, '_blank')
    })
}

const handleSubmit = async () => {
  try {
      // Ensure start_time is number
      const payload = { ...form, start_time: Number(form.start_time) }
      
    if (isEdit.value && currentId.value) {
      await request.put(`/admin/interviews/${currentId.value}`, payload)
    } else {
      await request.post('/admin/interviews', payload)
    }
    ElMessage.success(isEdit.value ? 'Updated successfully' : 'Created successfully')
    dialogVisible.value = false
    fetchInterviews()
  } catch (error) {
    // Error handled in interceptor
  }
}

onMounted(() => {
  fetchInterviews()
  fetchCandidates()
})
</script>
