<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">控制台</h1>

    <!-- Tabs -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit mb-6">
      <button v-for="tab in tabs" :key="tab.key" @click="activeTab = tab.key"
        class="px-4 py-2 rounded-lg text-sm font-medium transition"
        :class="activeTab === tab.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
        {{ tab.label }}
      </button>
    </div>

    <!-- Subscriptions -->
    <div v-if="activeTab === 'subs'">
      <div v-if="subs.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="sub in subs" :key="sub.id" class="bg-white rounded-xl border border-gray-200 p-5">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center font-bold">
              {{ (sub.capability_name || sub.name || '?').charAt(0) }}
            </div>
            <div>
              <h3 class="font-semibold text-gray-900">{{ sub.capability_name || sub.name }}</h3>
              <p class="text-xs text-gray-500">订阅于 {{ formatDate(sub.created_at) }}</p>
            </div>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-500">状态</span>
            <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="sub.status === 'active' ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-500'">
              {{ sub.status === 'active' ? '有效' : sub.status }}
            </span>
          </div>
          <button @click="goChat(sub)" class="mt-3 w-full py-2 border border-primary-500 text-primary-600 rounded-lg text-sm font-medium hover:bg-primary-50 transition">
            开始对话
          </button>
        </div>
      </div>
      <div v-else class="text-center py-16 text-gray-400">
        <p>暂无订阅的能力</p>
        <router-link to="/" class="text-primary-500 text-sm mt-2 inline-block">去市场逛逛 →</router-link>
      </div>
    </div>

    <!-- Usage -->
    <div v-if="activeTab === 'usage'">
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">使用统计</h2>
        <div v-if="usage.length" class="space-y-3">
          <div v-for="item in usage" :key="item.capability_id || item.name" class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
            <div>
              <p class="font-medium text-gray-800">{{ item.capability_name || item.name }}</p>
              <p class="text-xs text-gray-500">{{ item.capability_id }}</p>
            </div>
            <div class="text-right">
              <p class="font-semibold text-gray-900">{{ item.call_count || 0 }} 次</p>
              <p class="text-xs text-gray-500">花费 ¥{{ item.cost?.toFixed(2) || '0.00' }}</p>
            </div>
          </div>
        </div>
        <p v-else class="text-gray-400 text-sm">暂无使用记录</p>
      </div>
    </div>

    <!-- Bills -->
    <div v-if="activeTab === 'bills'">
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">账单记录</h2>
        <div v-if="bills.length">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="text-left py-2 text-gray-500 font-medium">时间</th>
                <th class="text-left py-2 text-gray-500 font-medium">描述</th>
                <th class="text-right py-2 text-gray-500 font-medium">金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="bill in bills" :key="bill.id" class="border-b border-gray-50">
                <td class="py-2 text-gray-600">{{ formatDate(bill.created_at) }}</td>
                <td class="py-2 text-gray-800">{{ bill.description || bill.type }}</td>
                <td class="py-2 text-right font-medium" :class="bill.amount > 0 ? 'text-green-600' : 'text-red-600'">
                  {{ bill.amount > 0 ? '+' : '' }}¥{{ Math.abs(bill.amount || 0).toFixed(2) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="text-gray-400 text-sm">暂无账单</p>
      </div>
    </div>

    <!-- API Keys -->
    <div v-if="activeTab === 'keys'">
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">API 密钥</h2>
        </div>
        <div v-if="apiKeys.length" class="space-y-3">
          <div v-for="key in apiKeys" :key="key.id" class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p class="font-mono text-sm text-gray-700">{{ maskKey(key.key || key.api_key) }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ key.capability_name || key.subscription_id }} · 创建于 {{ formatDate(key.created_at) }}</p>
            </div>
            <button @click="copyKey(key.key || key.api_key)" class="text-sm text-primary-500 hover:text-primary-700">
              复制
            </button>
          </div>
        </div>
        <p v-else class="text-gray-400 text-sm">暂无 API 密钥。订阅能力后可生成。</p>
      </div>
    </div>

    <!-- Recharge -->
    <div v-if="activeTab === 'recharge'">
      <div class="bg-white rounded-xl border border-gray-200 p-6 max-w-md">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">充值</h2>
        <div class="grid grid-cols-3 gap-3 mb-4">
          <button v-for="amount in [10, 50, 100, 200, 500, 1000]" :key="amount" @click="rechargeAmount = amount"
            class="py-3 rounded-xl border-2 text-center transition"
            :class="rechargeAmount === amount ? 'border-primary-500 bg-primary-50 text-primary-700 font-semibold' : 'border-gray-200 text-gray-700 hover:border-gray-300'">
            ¥{{ amount }}
          </button>
        </div>
        <div class="mb-4">
          <label class="text-sm text-gray-600">自定义金额</label>
          <input v-model.number="rechargeAmount" type="number" min="1"
            class="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none" />
        </div>
        <button @click="doRecharge" :disabled="recharging || !rechargeAmount"
          class="w-full py-2.5 bg-primary-500 text-white rounded-xl font-medium hover:bg-primary-600 disabled:opacity-50 transition">
          {{ recharging ? '处理中...' : `充值 ¥${rechargeAmount || 0}` }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardAPI, chatAPI } from '../api'

const router = useRouter()
const activeTab = ref('subs')
const subs = ref([])
const usage = ref([])
const bills = ref([])
const apiKeys = ref([])
const rechargeAmount = ref(100)
const recharging = ref(false)

const tabs = [
  { key: 'subs', label: '我的订阅' },
  { key: 'usage', label: '使用统计' },
  { key: 'bills', label: '账单' },
  { key: 'keys', label: 'API 密钥' },
  { key: 'recharge', label: '充值' },
]

function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }
function maskKey(key) { return key ? key.slice(0, 8) + '...' + key.slice(-4) : '' }
function copyKey(key) { navigator.clipboard.writeText(key).then(() => alert('已复制到剪贴板')) }

async function goChat(sub) {
  try {
    const capId = sub.capability_id || sub.cap_id
    const { data } = await chatAPI.createSession(capId)
    router.push({ name: 'chat', params: { sessionId: data.session_id } })
  } catch (e) {
    alert(e.response?.data?.detail || '创建会话失败')
  }
}

async function doRecharge() {
  recharging.value = true
  try {
    await dashboardAPI.recharge(rechargeAmount.value)
    alert('充值成功！')
  } catch (e) {
    alert(e.response?.data?.detail || '充值失败')
  } finally {
    recharging.value = false
  }
}

onMounted(async () => {
  try { const { data } = await dashboardAPI.subscriptions(); subs.value = data.items || data || [] } catch {}
  try { const { data } = await dashboardAPI.usage(); usage.value = data.items || data || [] } catch {}
  try { const { data } = await dashboardAPI.bills(); bills.value = data.items || data || [] } catch {}
  try { const { data } = await dashboardAPI.apiKeys(); apiKeys.value = data.items || data || [] } catch {}
})
</script>
