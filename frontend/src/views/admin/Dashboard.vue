<template>
  <div>
    <h2>Dashboard</h2>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>Positions</template>
          <div class="card-content">
            Manage open positions
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>Candidates</template>
          <div class="card-content">
            View candidates
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>Interviews</template>
          <div class="card-content">
            Track interviews
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.card-content {
  font-size: 14px;
  color: #666;
}
</style>
