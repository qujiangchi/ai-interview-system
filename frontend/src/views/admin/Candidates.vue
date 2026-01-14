<template>
  <div>
    <div class="flex justify-between mb-4">
      <h2>Candidates</h2>
      <el-button type="primary" @click="handleAdd">Add Candidate</el-button>
    </div>

    <el-table :data="candidates" border style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="email" label="Email" />
      <el-table-column label="Resume" width="120">
        <template #default="scope">
          <el-button size="small" link type="primary" @click="handleDownload(scope.row.id)">Download</el-button>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="120">
        <template #default="scope">
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="Add Candidate">
      <el-form :model="form" label-width="120px">
        <el-form-item label="Name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="Email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="Position">
           <el-select v-model="form.position_id" placeholder="Select Position">
            <el-option v-for="pos in positions" :key="pos.id" :label="pos.name" :value="pos.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Resume (PDF)">
          <input type="file" @change="handleFileChange" accept=".pdf" />
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

interface Candidate {
  id: number
  position_id: number
  name: string
  email: string
}

const candidates = ref<Candidate[]>([])
const positions = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({
  name: '',
  email: '',
  position_id: null as number | null,
  resume_content: null as File | null
})

const fetchCandidates = async () => {
  loading.value = true
  try {
    const res = await request.get<any, Candidate[]>('/admin/candidates')
    candidates.value = res
  } finally {
    loading.value = false
  }
}

const fetchPositions = async () => {
    const res = await request.get<any, any[]>('/admin/positions')
    positions.value = res
}

const handleAdd = () => {
  form.name = ''
  form.email = ''
  form.position_id = null
  form.resume_content = null
  dialogVisible.value = true
}

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    form.resume_content = target.files[0]
  }
}

const handleDelete = (row: Candidate) => {
  ElMessageBox.confirm('Are you sure to delete this candidate?', 'Warning', {
    confirmButtonText: 'OK',
    cancelButtonText: 'Cancel',
    type: 'warning'
  }).then(async () => {
    await request.delete(`/admin/candidates/${row.id}`)
    ElMessage.success('Delete completed')
    fetchCandidates()
  })
}

const handleDownload = (id: number) => {
    window.open(`/api/admin/candidates/${id}/resume`, '_blank')
}

const handleSubmit = async () => {
  if (!form.resume_content) {
      ElMessage.error("Please upload a resume")
      return
  }
  try {
    const formData = new FormData()
    formData.append('name', form.name)
    formData.append('email', form.email)
    formData.append('position_id', String(form.position_id))
    formData.append('resume_content', form.resume_content)
    
    // Custom request for FormData
    await request.post('/admin/candidates', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
    
    ElMessage.success('Created successfully')
    dialogVisible.value = false
    fetchCandidates()
  } catch (error) {
    // Error handled in interceptor
  }
}

onMounted(() => {
  fetchCandidates()
  fetchPositions()
})
</script>
