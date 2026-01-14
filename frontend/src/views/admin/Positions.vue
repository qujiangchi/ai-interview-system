<template>
  <div>
    <div class="flex justify-between mb-4">
      <h2>Positions</h2>
      <el-button type="primary" @click="handleAdd">Add Position</el-button>
    </div>

    <el-table :data="positions" border style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="Name" />
      <el-table-column prop="quantity" label="Quantity" width="100" />
      <el-table-column prop="status" label="Status" width="120">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="recruiter" label="Recruiter" />
      <el-table-column label="Actions" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">Edit</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? 'Edit Position' : 'Add Position'">
      <el-form :model="form" label-width="120px">
        <el-form-item label="Name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="Requirements">
          <el-input v-model="form.requirements" type="textarea" />
        </el-form-item>
        <el-form-item label="Responsibilities">
          <el-input v-model="form.responsibilities" type="textarea" />
        </el-form-item>
        <el-form-item label="Quantity">
          <el-input-number v-model="form.quantity" :min="1" />
        </el-form-item>
        <el-form-item label="Status">
          <el-select v-model="form.status">
            <el-option label="Pending" :value="0" />
            <el-option label="Open" :value="1" />
            <el-option label="Closed" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="Recruiter">
          <el-input v-model="form.recruiter" />
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

interface Position {
  id: number
  name: string
  requirements: string
  responsibilities: string
  quantity: number
  status: number
  recruiter: string
}

const positions = ref<Position[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive<Omit<Position, 'id'>>({
  name: '',
  requirements: '',
  responsibilities: '',
  quantity: 1,
  status: 0,
  recruiter: ''
})
const currentId = ref<number | null>(null)

const fetchPositions = async () => {
  loading.value = true
  try {
    const res = await request.get<any, Position[]>('/admin/positions')
    positions.value = res
  } finally {
    loading.value = false
  }
}

const getStatusText = (status: number) => {
  const map: Record<number, string> = { 0: 'Pending', 1: 'Open', 2: 'Closed' }
  return map[status] || 'Unknown'
}

const getStatusType = (status: number) => {
  const map: Record<number, string> = { 0: 'info', 1: 'success', 2: 'info' }
  return map[status] || ''
}

const handleAdd = () => {
  isEdit.value = false
  currentId.value = null
  Object.assign(form, {
    name: '',
    requirements: '',
    responsibilities: '',
    quantity: 1,
    status: 0,
    recruiter: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row: Position) => {
  isEdit.value = true
  currentId.value = row.id
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleDelete = (row: Position) => {
  ElMessageBox.confirm('Are you sure to delete this position?', 'Warning', {
    confirmButtonText: 'OK',
    cancelButtonText: 'Cancel',
    type: 'warning'
  }).then(async () => {
    await request.delete(`/admin/positions/${row.id}`)
    ElMessage.success('Delete completed')
    fetchPositions()
  })
}

const handleSubmit = async () => {
  try {
    if (isEdit.value && currentId.value) {
      await request.put(`/admin/positions/${currentId.value}`, form)
    } else {
      await request.post('/admin/positions', form)
    }
    ElMessage.success(isEdit.value ? 'Updated successfully' : 'Created successfully')
    dialogVisible.value = false
    fetchPositions()
  } catch (error) {
    // Error handled in interceptor
  }
}

onMounted(() => {
  fetchPositions()
})
</script>
