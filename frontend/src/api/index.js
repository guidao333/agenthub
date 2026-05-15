import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Auth
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
}

// Market
export const marketAPI = {
  list: (params) => api.get('/market/capabilities', { params }),
  detail: (capId) => api.get(`/market/capabilities/${capId}`),
  categories: () => api.get('/market/categories'),
  hot: () => api.get('/market/hot'),
  subscribe: (capId) => api.post(`/market/capabilities/${capId}/subscribe`),
}

// Chat
export const chatAPI = {
  createSession: (capability_id) => api.post('/chat/sessions', { capability_id }),
  sendMessage: (sessionId, message) => {
    const token = localStorage.getItem('token')
    return fetch(`/api/chat/sessions/${sessionId}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message }),
    })
  },
  history: (sessionId) => api.get(`/chat/sessions/${sessionId}/history`),
  deleteSession: (sessionId) => api.delete(`/chat/sessions/${sessionId}`),
  listSessions: () => api.get('/chat/sessions'),
}

// Dashboard
export const dashboardAPI = {
  subscriptions: () => api.get('/dashboard/subscriptions'),
  usage: (period = 'month') => api.get('/dashboard/usage', { params: { period } }),
  bills: () => api.get('/dashboard/bills'),
  recharge: (amount) => api.post('/dashboard/recharge', { amount }),
  apiKeys: () => api.get('/dashboard/api-keys'),
  createApiKey: (subscription_id) => api.post('/dashboard/api-keys', { subscription_id }),
}

// Developer
export const developerAPI = {
  capabilities: () => api.get('/developer/capabilities'),
  create: (data) => api.post('/developer/capabilities', data),
  update: (capId, data) => api.put(`/developer/capabilities/${capId}`, data),
  submit: (capId) => api.post(`/developer/capabilities/${capId}/submit`),
  earnings: () => api.get('/developer/earnings'),
  earningsDetail: () => api.get('/developer/earnings/detail'),
  withdraw: (amount) => api.post('/developer/withdraw', { amount }),
}

// Admin
export const adminAPI = {
  pendingReviews: () => api.get('/admin/reviews/pending'),
  approve: (capId) => api.post(`/admin/reviews/${capId}/approve`),
  reject: (capId) => api.post(`/admin/reviews/${capId}/reject`),
  users: (params) => api.get('/admin/users', { params }),
  finance: () => api.get('/admin/finance/overview'),
  stats: () => api.get('/admin/stats'),
}

export default api
