<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">管理后台</h1>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div v-for="stat in statCards" :key="stat.label" class="bg-white rounded-xl border border-gray-200 p-5">
        <p class="text-sm text-gray-500 mb-1">{{ stat.label }}</p>
        <p class="text-2xl font-bold" :class="stat.color || 'text-gray-900'">{{ stat.value }}</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit mb-6">
      <button v-for="tab in tabs" :key="tab.key" @click="activeTab = tab.key"
        class="px-4 py-2 rounded-lg text-sm font-medium transition"
        :class="activeTab === tab.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
        {{ tab.label }}
        <span v-if="tab.count" class="ml-1 px-1.5 py-0.5 bg-red-500 text-white text-xs rounded-full">{{ tab.count }}</span>
      </button>
    </div>

    <!-- Pending Reviews -->
    <div v-if="activeTab === 'reviews'">
      <div v-if="pendingReviews.length" class="space-y-4">
        <div v-for="cap in pendingReviews" :key="cap.cap_id" class="bg-white rounded-xl border border-gray-200 p-5">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2">
                <h3 class="font-semibold text-gray-900">{{ cap.name }}</h3>
                <span class="px-2 py-0.5 bg-yellow-50 text-yellow-600 text-xs rounded-full">待审核</span>
              </div>
              <p class="text-sm text-gray-600 mb-2">{{ cap.description }}</p>
              <div class="flex items-center gap-4 text-xs text-gray-500">
                <span>开发者: {{ cap.developer_name || '-' }}</span>
                <span>分类: {{ cap.category }}</span>
                <span>计费: {{ cap.pricing_model }}</span>
                <span v-if="cap.price">价格: ¥{{ cap.price }}</span>
              </div>
            </div>
            <div class="flex gap-2 ml-4">
              <button @click="approveCap(cap.cap_id)" class="px-4 py-2 bg-green-500 text-white rounded-lg text-sm font-medium hover:bg-green-600 transition">
                通过
              </button>
              <button @click="rejectCap(cap.cap_id)" class="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition">
                拒绝
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-16 text-gray-400">
        <p>暂无待审核能力</p>
      </div>
    </div>

    <!-- Users -->
    <div v-if="activeTab === 'users'">
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">用户管理</h2>
          <div class="flex gap-2">
            <select v-model="userFilterRole" @change="loadUsers" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="">全部角色</option>
              <option value="customer">客户</option>
              <option value="developer">开发者</option>
              <option value="admin">管理员</option>
            </select>
          </div>
        </div>
        <table v-if="users.length" class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-200">
              <th class="text-left py-2 text-gray-500 font-medium">用户名</th>
              <th class="text-left py-2 text-gray-500 font-medium">邮箱</th>
              <th class="text-left py-2 text-gray-500 font-medium">角色</th>
              <th class="text-left py-2 text-gray-500 font-medium">状态</th>
              <th class="text-left py-2 text-gray-500 font-medium">注册时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id || user.username" class="border-b border-gray-50">
              <td class="py-2 text-gray-900 font-medium">{{ user.username }}</td>
              <td class="py-2 text-gray-600">{{ user.email || '-' }}</td>
              <td class="py-2">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="roleClass(user.role)">
                  {{ { customer: '客户', developer: '开发者', admin: '管理员' }[user.role] || user.role }}
                </span>
              </td>
              <td class="py-2">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="user.status === 'active' ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-500'">
                  {{ user.status === 'active' ? '正常' : user.status || '正常' }}
                </span>
              </td>
              <td class="py-2 text-gray-500">{{ formatDate(user.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-gray-400 text-sm">暂无用户数据</p>
      </div>
    </div>

    <!-- Finance -->
    <div v-if="activeTab === 'finance'">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-white rounded-xl border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">平台总收入</p>
          <p class="text-2xl font-bold text-green-600">¥{{ finance.total_revenue?.toFixed(2) || '0.00' }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">开发者分成</p>
          <p class="text-2xl font-bold text-primary-600">¥{{ finance.developer_payout?.toFixed(2) || '0.00' }}</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">平台利润</p>
          <p class="text-2xl font-bold text-amber-600">¥{{ finance.platform_profit?.toFixed(2) || '0.00' }}</p>
        </div>
      </div>
    </div>

    <!-- Platform Stats -->
    <div v-if="activeTab === 'stats'">
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">平台统计</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div v-for="s in platformStats" :key="s.label" class="text-center">
            <p class="text-3xl font-bold text-gray-900">{{ s.value }}</p>
            <p class="text-sm text-gray-500 mt-1">{{ s.label }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminAPI } from '../api'

const activeTab = ref('reviews')
const pendingReviews = ref([])
const users = ref([])
const finance = ref({})
const platformStats = ref([])
const userFilterRole = ref('')

const tabs = computed(() => [
  { key: 'reviews', label: '审核', count: pendingReviews.value.length },
  { key: 'users', label: '用户' },
  { key: 'finance', label: '财务' },
  { key: 'stats', label: '统计' },
])

const statCards = computed(() => [
  { label: '待审核', value: pendingReviews.value.length, color: 'text-yellow-600' },
  { label: '总用户', value: platformStats.value.find(s => s.label === '总用户')?.value || users.value.length, color: 'text-primary-600' },
  { label: '总能力', value: platformStats.value.find(s => s.label === '总能力')?.value || '-', color: 'text-gray-900' },
  { label: '总收入', value: `¥${(finance.value.total_revenue || 0).toFixed(2)}`, color: 'text-green-600' },
])

function roleClass(role) {
  const m = { customer: 'bg-blue-50 text-blue-600', developer: 'bg-purple-50 text-purple-600', admin: 'bg-red-50 text-red-600' }
  return m[role] || 'bg-gray-100 text-gray-600'
}

function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }

async function approveCap(capId) {
  try { await adminAPI.approve(capId); loadPending() } catch (e) { alert(e.response?.data?.detail || '操作失败') }
}

async function rejectCap(capId) {
  const reason = prompt('拒绝原因:')
  if (!reason) return
  try { await adminAPI.reject(capId); loadPending() } catch (e) { alert(e.response?.data?.detail || '操作失败') }
}

async function loadPending() {
  try { const { data } = await adminAPI.pendingReviews(); pendingReviews.value = data.items || data || [] } catch {}
}

async function loadUsers() {
  try {
    const params = {}
    if (userFilterRole.value) params.role = userFilterRole.value
    const { data } = await adminAPI.users(params)
    users.value = data.items || data || []
  } catch {}
}

async function loadFinance() {
  try { const { data } = await adminAPI.finance(); finance.value = data } catch {}
}

async function loadStats() {
  try {
    const { data } = await adminAPI.stats()
    if (Array.isArray(data)) {
      platformStats.value = data
    } else {
      platformStats.value = Object.entries(data).map(([k, v]) => ({
        label: { total_users: '总用户', total_capabilities: '总能力', total_calls: '总调用', total_revenue: '总收入' }[k] || k,
        value: typeof v === 'number' && k.includes('revenue') ? `¥${v.toFixed(2)}` : String(v),
      }))
    }
  } catch {}
}

onMounted(() => {
  loadPending()
  loadUsers()
  loadFinance()
  loadStats()
})
</script>
