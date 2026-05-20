import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { guest: true } },
  { path: '/register', name: 'register', component: () => import('../views/Register.vue'), meta: { guest: true } },
  { path: '/', name: 'market', component: () => import('../views/MarketHome.vue') },
  { path: '/capability/:capId', name: 'capability', component: () => import('../views/CapabilityDetail.vue') },
  { path: '/dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { auth: true } },
  { path: '/chat/:sessionId?', name: 'chat', component: () => import('../views/ChatWindow.vue'), meta: { auth: true } },
  { path: '/developer', name: 'developer', component: () => import('../views/DeveloperPortal.vue'), meta: { auth: true, roles: ['developer', 'admin'] } },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminPanel.vue'), meta: { auth: true, role: 'admin' } },
  { path: '/vision', name: 'vision', component: () => import('../views/VisionPanel.vue'), meta: { auth: true, role: 'admin' } },,
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')

  if (to.meta.auth && !token) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }
  if (to.meta.role && to.meta.role !== role) {
    return next({ name: 'market' })
  }
  if (to.meta.roles && !to.meta.roles.includes(role)) {
    return next({ name: 'market' })
  }
  if (to.meta.guest && token) {
    return next({ name: 'market' })
  }
  next()
})

export default router
