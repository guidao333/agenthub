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
  clientStatus: () => api.get('/dashboard/client-status'),
}

// Config
export const configAPI = {
  categories: () => api.get('/config/categories'),
  categoryTree: () => api.get('/config/categories/tree'),
  tags: () => api.get('/config/tags'),
  levels: () => api.get('/config/levels'),
}

// Developer
export const developerAPI = {
  capabilities: () => api.get('/developer/capabilities'),
  create: (data) => api.post('/developer/capabilities', data),
  update: (capId, data) => api.put(`/developer/capabilities/${capId}`, data),
  submit: (capId) => api.post(`/developer/capabilities/${capId}/submit`),
  uploadVersion: (capId, data) => {
    const form = new FormData()
    form.append('version', data.version)
    form.append('changelog', data.changelog || '')
    form.append('package', data.package)
    return api.post(`/developer/capabilities/${capId}/versions`, form)
  },
  earnings: () => api.get('/developer/earnings'),
  earningsDetail: () => api.get('/developer/earnings/detail'),
  withdraw: (amount) => api.post('/developer/withdraw', null, { params: { amount } }),
}

// Admin
export const adminAPI = {
  pendingReviews: () => api.get('/admin/reviews/pending'),
  approve: (capId) => api.post(`/admin/reviews/${capId}/approve`),
  reject: (capId) => api.post(`/admin/reviews/${capId}/reject`),
  users: (params) => api.get('/admin/users', { params }),
  suspendUser: (uid) => api.post(`/admin/users/${uid}/suspend`),
  activateUser: (uid) => api.post(`/admin/users/${uid}/activate`),
  finance: () => api.get('/admin/finance/overview'),
  withdrawals: (status) => api.get('/admin/finance/withdrawals', { params: { status } }),
  approveWithdrawal: (wid) => api.post(`/admin/finance/withdrawals/${wid}/approve`),
  rejectWithdrawal: (wid) => api.post(`/admin/finance/withdrawals/${wid}/reject`),
  stats: () => api.get('/admin/stats'),
  // Categories
  categories: () => api.get('/admin/categories'),
  createCategory: (data) => api.post('/admin/categories', data),
  updateCategory: (catId, data) => api.put(`/admin/categories/${catId}`, data),
  deleteCategory: (catId) => api.delete(`/admin/categories/${catId}`),
  // Capabilities
  listCaps: (params) => api.get('/admin/capabilities', { params }),
  createCap: (data) => api.post('/admin/capabilities', data),
  updateCap: (capId, data) => api.put(`/admin/capabilities/${capId}`, data),
  deleteCap: (capId) => api.delete(`/admin/capabilities/${capId}`),
  // Pricing
  updatePricing: (capId, data) => api.put(`/admin/pricing/${capId}`, data),
  batchPricing: (data) => api.post('/admin/pricing/batch', data),
}

// Cap Config
export const capConfigAPI = {
  myConfig: (capId) => api.get(`/cap-config/my-config/${capId}`),
  adapterOptions: (capId) => api.get(`/cap-config/adapter-options/${capId}`),
  save: (capId, config) => api.post('/cap-config/save', { cap_id: capId, config }),
  test: (capId, config) => api.post('/cap-config/test', { cap_id: capId, config }),
}

// Capability Chat
export const capChatAPI = {
  createSession: (capId) => api.post('/capability-chat/sessions', { cap_id: capId }),
  chat: (sessionId, message) => api.post('/capability-chat/chat', { session_id: sessionId, message }),
}

// Vision AI
export const visionAPI = {
  // 设备
  devices: () => api.get('/vision/devices'),
  registerDevice: (data) => api.post('/vision/devices', data),
  deleteDevice: (id) => api.delete(`/vision/devices/${id}`),
  // 摄像头
  cameras: (deviceId) => api.get('/vision/cameras', { params: { device_id: deviceId } }),
  addCamera: (data) => api.post('/vision/cameras', data),
  // 事件
  events: (params) => api.get('/vision/events', { params }),
  acknowledgeEvent: (id) => api.post(`/vision/events/${id}/acknowledge`),
  // 通知渠道
  channels: () => api.get('/vision/notify/channels'),
  addChannel: (data) => api.post('/vision/notify/channels', data),
  testChannel: (id) => api.post(`/vision/notify/test/${id}`),
  // 规则
  rules: (capability) => api.get('/vision/rules', { params: { capability } }),
  createRule: (data) => api.post('/vision/rules', data),
  updateRule: (id, data) => api.put(`/vision/rules/${id}`, data),
  // 统计
  stats: (deviceId) => api.get('/vision/stats', { params: { device_id: deviceId } }),
}

export default api
