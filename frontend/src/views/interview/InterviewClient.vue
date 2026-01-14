<template>
  <div class="interview-container">
    <div v-if="loading" class="center-content">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <p>Loading...</p>
    </div>
    
    <div v-else-if="error" class="center-content">
      <el-result icon="error" title="Error" :sub-title="error"></el-result>
    </div>

    <div v-else-if="info.status === 0" class="center-content">
      <el-result icon="info" title="Not Started" sub-title="The interview has not started yet. Please check back later.">
         <template #extra>
            <p>Scheduled Time: {{ info.time }}</p>
         </template>
      </el-result>
    </div>

    <div v-else-if="isFinished || info.status === 3" class="center-content">
       <el-result icon="success" title="Completed" sub-title="You have completed the interview. Thank you!">
         <template #extra>
            <p>This window will close in {{ countdown }} seconds...</p>
         </template>
       </el-result>
    </div>

    <div v-else class="main-content">
       <!-- Welcome Screen -->
       <el-card v-if="!started" class="welcome-card">
          <template #header>
            <h2 class="text-center">Interview Welcome</h2>
          </template>
          <div class="info-list">
            <p><strong>Candidate:</strong> {{ info.candidate }}</p>
            <p><strong>Position:</strong> {{ info.position }}</p>
            <p><strong>Time:</strong> {{ info.time }}</p>
          </div>
          <div class="text-center mt-8">
            <el-button type="primary" size="large" @click="startInterview">Start Interview</el-button>
          </div>
       </el-card>

       <!-- Question Screen -->
       <el-card v-else class="question-card">
          <template #header>
             <div class="flex justify-between items-center">
               <span>Question {{ currentIndex + 1 }} / {{ info.question_count }}</span>
               <div class="flex items-center gap-2">
                 <span>Voice Reading</span>
                 <el-switch v-model="voiceReading" @change="toggleVoiceReading" />
               </div>
             </div>
             <el-progress :percentage="progress" :status="progress === 100 ? 'success' : ''" class="mt-2" />
          </template>
          
          <div class="question-body">
             <h3 class="question-text">{{ currentQuestion.text }}</h3>
             <el-button v-if="voiceReading" text circle @click="readQuestion(currentQuestion.text)">
                <el-icon><Headset /></el-icon>
             </el-button>
          </div>

          <div class="answer-area">
             <div v-if="isRecording" class="recording-status">
                <div class="recording-dot"></div>
                <span>Recording: {{ formatTime(recordingTime) }}</span>
             </div>
             
             <div class="controls">
                <el-button 
                  v-if="!isRecording" 
                  type="primary" 
                  size="large" 
                  circle 
                  class="record-btn"
                  @click="startRecording"
                  :disabled="submitting"
                >
                   <el-icon :size="24"><Microphone /></el-icon>
                </el-button>
                
                <el-button 
                  v-else 
                  type="danger" 
                  size="large" 
                  circle 
                  class="record-btn"
                  @click="stopRecording"
                >
                   <el-icon :size="24"><VideoPause /></el-icon>
                </el-button>
             </div>
             <p class="hint-text">{{ isRecording ? 'Click to stop and submit' : 'Click microphone to start answering' }}</p>
             <p v-if="submitting" class="text-gray-500">Submitting answer...</p>
          </div>
       </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import request from '@/utils/request'
import { Loading, Microphone, VideoPause, Headset } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const token = route.params.token as string

const loading = ref(true)
const error = ref('')
const info = ref<any>({})
const started = ref(false)
const isFinished = ref(false)
const countdown = ref(5)
const currentIndex = ref(0)
const currentQuestion = ref<any>({})
const voiceReading = ref(true)
const isRecording = ref(false)
const recordingTime = ref(0)
const submitting = ref(false)
let timer: any = null
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

const progress = computed(() => {
   if (!info.value.question_count) return 0
   return Math.round(((currentIndex.value + 1) / info.value.question_count) * 100)
})

const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const handleFinished = () => {
    isFinished.value = true
    const timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) {
            clearInterval(timer)
            window.close()
            // Fallback if window.close() is blocked
            window.location.href = '/admin/interviews' 
        }
    }, 1000)
}

const fetchInfo = async () => {
    try {
        const res = await request.get(`/interview/${token}/info`)
        info.value = res
        voiceReading.value = Boolean(info.value.voice_reading)
        if (info.value.status === 3) {
            handleFinished()
        }
    } catch (e: any) {
        error.value = e.response?.data?.error || 'Failed to load interview info'
    } finally {
        loading.value = false
    }
}

const startInterview = async () => {
    started.value = true
    fetchQuestion()
}

const fetchQuestion = async () => {
    try {
        const res: any = await request.get(`/interview/${token}/get_question`, {
            params: { current_id: currentQuestion.value.id || 0 }
        })
        if (res.id === 0) {
            handleFinished()
        } else {
            currentQuestion.value = res
            if (voiceReading.value) {
                readQuestion(res.text)
            }
        }
    } catch (e) {
        ElMessage.error('Failed to get question')
    }
}

const toggleVoiceReading = async () => {
    try {
        await request.post(`/interview/${token}/toggle_voice_reading`, {
            enabled: voiceReading.value
        })
    } catch (e) {
        // ignore
    }
}

const readQuestion = (text: string) => {
    if (!voiceReading.value) return
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    window.speechSynthesis.speak(utterance)
}

const startRecording = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        mediaRecorder = new MediaRecorder(stream)
        audioChunks = []
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data)
        }
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
            await submitAnswer(audioBlob)
            stream.getTracks().forEach(track => track.stop())
        }
        
        mediaRecorder.start()
        isRecording.value = true
        recordingTime.value = 0
        timer = setInterval(() => {
            recordingTime.value++
        }, 1000)
        
    } catch (e) {
        ElMessage.error('Could not access microphone. Please allow permission.')
    }
}

const stopRecording = () => {
    if (mediaRecorder && isRecording.value) {
        mediaRecorder.stop()
        isRecording.value = false
        clearInterval(timer)
    }
}

const submitAnswer = async (audioBlob: Blob) => {
    submitting.value = true
    try {
        const formData = new FormData()
        formData.append('question_id', String(currentQuestion.value.id))
        formData.append('audio_answer', audioBlob, 'answer.wav')
        
        const res: any = await request.post(`/interview/${token}/submit_answer`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        
        if (res.next_question) {
            if (res.next_question.id === 0) {
                handleFinished()
            } else {
                currentQuestion.value = res.next_question
                currentIndex.value++
                if (voiceReading.value) {
                    readQuestion(currentQuestion.value.text)
                }
            }
        }
    } catch (e) {
        ElMessage.error('Failed to submit answer')
    } finally {
        submitting.value = false
    }
}

onMounted(() => {
    fetchInfo()
})
</script>

<style scoped>
.interview-container {
    min-height: 100vh;
    background-color: #f5f7fa;
    padding: 20px;
    display: flex;
    justify-content: center;
    align-items: center;
}
.center-content {
    text-align: center;
}
.main-content {
    width: 100%;
    max-width: 600px;
}
.welcome-card, .question-card {
    background: white;
}
.info-list p {
    margin: 10px 0;
    font-size: 16px;
}
.question-body {
    min-height: 150px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 20px 0;
}
.question-text {
    font-size: 20px;
    margin-bottom: 10px;
}
.answer-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding-top: 20px;
    border-top: 1px solid #eee;
}
.record-btn {
    width: 64px;
    height: 64px;
}
.recording-status {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #f56c6c;
    font-weight: bold;
}
.recording-dot {
    width: 10px;
    height: 10px;
    background-color: #f56c6c;
    border-radius: 50%;
    animation: pulse 1s infinite;
}
@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}
</style>
