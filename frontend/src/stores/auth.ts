import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/utils/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')

  const login = async (loginForm: any) => {
    try {
      const res: any = await request.post('/auth/login', loginForm)
      token.value = res.token
      username.value = res.username
      localStorage.setItem('token', res.token)
      localStorage.setItem('username', res.username)
      return true
    } catch (error) {
      return false
    }
  }

  const logout = () => {
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
  }

  return {
    token,
    username,
    login,
    logout,
  }
})
