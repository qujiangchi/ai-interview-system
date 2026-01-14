import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/admin/Login.vue'
import Layout from '@/views/admin/Layout.vue'
import Dashboard from '@/views/admin/Dashboard.vue'
import Positions from '@/views/admin/Positions.vue'
import Candidates from '@/views/admin/Candidates.vue'
import Interviews from '@/views/admin/Interviews.vue'
// We will add Interview Client component later

const routes = [
  {
    path: '/',
    redirect: '/admin/login'
  },
  {
    path: '/admin/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/admin',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: Dashboard
      },
      {
        path: 'positions',
        name: 'Positions',
        component: Positions
      },
      {
        path: 'candidates',
        name: 'Candidates',
        component: Candidates
      },
      {
        path: 'interviews',
        name: 'Interviews',
        component: Interviews
      }
    ]
  },
  {
      path: '/interview/:token',
      name: 'InterviewClient',
      component: () => import('@/views/interview/InterviewClient.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/admin/login')
  } else {
    next()
  }
})

export default router
