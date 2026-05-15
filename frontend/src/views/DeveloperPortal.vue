<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">开发者中心</h1>
      <button @click="showCreateForm = true" class="px-4 py-2 bg-primary-500 text-white rounded-xl text-sm font-medium hover:bg-primary-600 transition flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        创建能力
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <p class="text-sm text-gray-500 mb-1">总能力数</p>
        <p class="text-2xl font-bold text-gray-900">{{ myCaps.length }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <p class="text-sm text-gray-500 mb-1">总调用</p>
        <p class="text-2xl font-bold text-gray-900">{{ totalCalls }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <p class="text-sm text-gray-500 mb-1">总收入</p>
        <p class="text-2xl font-bold text-green-600">¥{{ totalEarnings.toFixed(2) }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <p class="text-sm text-gray-500 mb-1">可提现</p>
        <p class="text-2xl font-bold text-primary-600">¥{{ availableBalance.toFixed(2) }}</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit mb-6">
      <button v-for="tab in tabs" :key="tab.key" @click="activeTab = tab.key"
        class="px-4 py-2 rounded-lg text-sm font-medium transition"
        :class="activeTab === tab.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
        {{ tab.label }}
      </button>
    </div>

    <!-- My Capabilities -->
    <div v-if="activeTab === 'caps'">
      <div v-if="myCaps.length" class="space-y-4">
        <div v-for="cap in myCaps" :key="cap.cap_id" class="bg-white rounded-xl border border-gray-200 p-5">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center text-lg font-bold">
                {{ cap.name.charAt(0) }}
              </div>
              <div>
                <h3 class="font-semibold text-gray-900">{{ cap.name }}</h3>
                <p class="text-sm text-gray-500 mt-0.5">{{ cap.category }} · {{ cap.pricing_model }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="px-2.5 py-1 rounded-full text-xs font-medium" :class="statusClass(cap.status)">
                {{ statusLabel(cap.status) }}
              </span>
            </div>
          </div>
          <p class="text-sm text-gray-600 mt-3">{{ cap.description }}</p>
          <div class="flex items-center gap-4 mt-4 text-sm">
            <span class="text-gray-500">调用: <b class="text-gray-700">{{ cap.call_count || 0 }}</b></span>
            <span class="text-gray-500">评分: <b class="text-gray-700">{{ cap.avg_rating?.toFixed(1) || '-' }}</b></span>
          </div>
          <div class="flex gap-2 mt-4">
            <button v-if="cap.status === 'draft'" @click="submitCap(cap.cap_id)" class="px-3 py-1.5 bg-primary-500 text-white rounded-lg text-xs font-medium hover:bg-primary-600">
              提交审核
            </button>
            <button @click="editCap(cap)" class="px-3 py-1.5 border border-gray-300 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-50">
              编辑
            </button>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-16 text-gray-400">
        <p>还没有创建能力</p>
        <button @click="showCreateForm = true" class="text-primary-500 text-sm mt-2">创建第一个 →</button>
      </div>
    </div>

    <!-- Earnings -->
    <div v-if="activeTab === 'earnings'">
      <div class="bg-white rounded-xl border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">收入明细</h2>
        <div v-if="earningsDetail.length">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="text-left py-2 text-gray-500 font-medium">时间</th>
                <th class="text-left py-2 text-gray-500 font-medium">来源</th>
                <th class="text-right py-2 text-gray-500 font-medium">金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in earningsDetail" :key="idx" class="border-b border-gray-50">
                <td class="py-2 text-gray-600">{{ formatDate(item.created_at) }}</td>
                <td class="py-2 text-gray-800">{{ item.capability_name || item.description || '-' }}</td>
                <td class="py-2 text-right font-medium text-green-600">+¥{{ (item.amount || 0).toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="text-gray-400 text-sm">暂无收入记录</p>

        <div class="mt-6 pt-4 border-t border-gray-200">
          <h3 class="font-medium text-gray-900 mb-3">提现</h3>
          <div class="flex gap-3 max-w-sm">
            <input v-model.number="withdrawAmount" type="number" min="1" placeholder="提现金额"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
            <button @click="doWithdraw" :disabled="withdrawing" class="px-4 py-2 bg-primary-500 text-white rounded-lg text-sm font-medium hover:bg-primary-600 disabled:opacity-50">
              {{ withdrawing ? '处理中...' : '提现' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showCreateForm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="showCreateForm = false">
      <div class="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
        <h2 class="text-xl font-bold text-gray-900 mb-6">{{ editingCap ? '编辑能力' : '创建新能力' }}</h2>
        <form @submit.prevent="saveCap" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">能力 ID</label>
              <input v-model="capForm.cap_id" :disabled="!!editingCap" required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none disabled:bg-gray-50"
                placeholder="如: broadband-diagnosis" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <input v-model="capForm.name" required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                placeholder="能力名称" />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea v-model="capForm.description" rows="3" required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="描述你的AI能力..." />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">分类</label>
              <input v-model="capForm.category" required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                placeholder="如: ISP网络" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">标签（逗号分隔）</label>
              <input v-model="capForm.tagsInput"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                placeholder="如: 宽带,故障,诊断" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">计费模式</label>
              <select v-model="capForm.pricing_model"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none">
                <option value="free">免费</option>
                <option value="per_call">按次计费</option>
                <option value="monthly">包月</option>
              </select>
            </div>
            <div v-if="capForm.pricing_model !== 'free'">
              <label class="block text-sm font-medium text-gray-700 mb-1">价格 (¥)</label>
              <input v-model.number="capForm.price" type="number" min="0" step="0.01"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
            </div>
          </div>

          <div v-if="formError" class="p-3 bg-red-50 text-red-600 text-sm rounded-lg">{{ formError }}</div>

          <div class="flex gap-3 pt-2">
            <button type="submit" :disabled="saving"
              class="px-6 py-2 bg-primary-500 text-white rounded-xl font-medium hover:bg-primary-600 disabled:opacity-50">
              {{ saving ? '保存中...' : (editingCap ? '更新' : '创建') }}
            </button>
            <button type="button" @click="showCreateForm = false" class="px-6 py-2 border border-gray-300 rounded-xl text-gray-600 hover:bg-gray-50">
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { developerAPI } from '../api'

const activeTab = ref('caps')
const myCaps = ref([])
const earningsDetail = ref([])
const showCreateForm = ref(false)
const editingCap = ref(null)
const saving = ref(false)
const formError = ref('')
const withdrawAmount = ref(0)
const withdrawing = ref(false)

const capForm = reactive({
  cap_id: '', name: '', description: '', category: '', tagsInput: '',
  pricing_model: 'free', price: 0,
})

const tabs = [
  { key: 'caps', label: '我的能力' },
  { key: 'earnings', label: '收入' },
]

const totalCalls = computed(() => myCaps.value.reduce((s, c) => s + (c.call_count || 0), 0))
const totalEarnings = computed(() => {
  const detail = earningsDetail.value
  return Array.isArray(detail) ? detail.reduce((s, d) => s + (d.amount || 0), 0) : 0
})
const availableBalance = computed(() => totalEarnings.value) // simplified

function statusClass(s) {
  const m = { draft: 'bg-gray-100 text-gray-600', pending: 'bg-yellow-50 text-yellow-600', approved: 'bg-green-50 text-green-600', rejected: 'bg-red-50 text-red-600' }
  return m[s] || m.draft
}
function statusLabel(s) {
  const m = { draft: '草稿', pending: '审核中', approved: '已上线', rejected: '已拒绝' }
  return m[s] || s || '草稿'
}
function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }

function editCap(cap) {
  editingCap.value = cap
  Object.assign(capForm, {
    cap_id: cap.cap_id, name: cap.name, description: cap.description,
    category: cap.category, tagsInput: (cap.tags || []).join(', '),
    pricing_model: cap.pricing_model || 'free', price: cap.price || 0,
  })
  showCreateForm.value = true
}

function resetForm() {
  editingCap.value = null
  Object.assign(capForm, { cap_id: '', name: '', description: '', category: '', tagsInput: '', pricing_model: 'free', price: 0 })
  formError.value = ''
}

async function saveCap() {
  formError.value = ''
  saving.value = true
  const payload = {
    cap_id: capForm.cap_id,
    name: capForm.name,
    description: capForm.description,
    category: capForm.category,
    tags: capForm.tagsInput.split(',').map(t => t.trim()).filter(Boolean),
    pricing_model: capForm.pricing_model,
    price: capForm.pricing_model === 'free' ? 0 : capForm.price,
  }
  try {
    if (editingCap.value) {
      await developerAPI.update(editingCap.value.cap_id, payload)
    } else {
      await developerAPI.create(payload)
    }
    showCreateForm.value = false
    resetForm()
    loadCaps()
  } catch (e) {
    formError.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function submitCap(capId) {
  try {
    await developerAPI.submit(capId)
    loadCaps()
  } catch (e) {
    alert(e.response?.data?.detail || '提交失败')
  }
}

async function doWithdraw() {
  if (!withdrawAmount.value || withdrawAmount.value <= 0) return alert('请输入有效金额')
  withdrawing.value = true
  try {
    await developerAPI.withdraw(withdrawAmount.value)
    alert('提现申请已提交')
    withdrawAmount.value = 0
  } catch (e) {
    alert(e.response?.data?.detail || '提现失败')
  } finally {
    withdrawing.value = false
  }
}

async function loadCaps() {
  try { const { data } = await developerAPI.capabilities(); myCaps.value = data.items || data || [] } catch {}
}
async function loadEarnings() {
  try {
    const { data } = await developerAPI.earningsDetail()
    earningsDetail.value = Array.isArray(data) ? data : (data.items || [])
  } catch {}
}

onMounted(() => { loadCaps(); loadEarnings() })
</script>
