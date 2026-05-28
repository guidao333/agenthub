<template>
  <div class="bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-6">
        <div>
          <p class="text-sm font-semibold text-primary-600">Developer</p>
          <h1 class="mt-1 text-2xl font-bold text-gray-950">开发者中心</h1>
          <p class="mt-2 text-sm text-gray-600">
            创建能力草稿，完善定价和标签，提交审核后即可进入能力市场。
          </p>
        </div>
        <button
          type="button"
          @click="openCreateForm"
          class="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          创建能力
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-white rounded-lg border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">我的能力</p>
          <p class="text-2xl font-bold text-gray-950">{{ myCaps.length }}</p>
        </div>
        <div class="bg-white rounded-lg border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">总调用</p>
          <p class="text-2xl font-bold text-gray-950">{{ formatNumber(totalCalls) }}</p>
        </div>
        <div class="bg-white rounded-lg border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">累计收益</p>
          <p class="text-2xl font-bold text-emerald-600">¥{{ totalEarnings.toFixed(2) }}</p>
        </div>
        <div class="bg-white rounded-lg border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">可提现</p>
          <p class="text-2xl font-bold text-primary-600">¥{{ availableBalance.toFixed(2) }}</p>
        </div>
      </div>

      <div class="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit mb-6">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          @click="activeTab = tab.key"
          class="px-4 py-2 rounded-md text-sm font-medium transition"
          :class="activeTab === tab.key ? 'bg-white text-gray-950 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        >
          {{ tab.label }}
        </button>
      </div>

      <section v-if="activeTab === 'caps'">
        <div v-if="myCaps.length" class="space-y-4">
          <article v-for="cap in myCaps" :key="cap.cap_id" class="bg-white rounded-lg border border-gray-200 p-5">
            <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div class="flex items-start gap-3 min-w-0">
                <div class="w-12 h-12 rounded-lg bg-primary-50 text-primary-700 flex items-center justify-center text-lg font-bold shrink-0">
                  {{ cap.name?.charAt(0) || 'A' }}
                </div>
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <h3 class="font-semibold text-gray-950">{{ cap.name }}</h3>
                    <span class="px-2.5 py-1 rounded-full text-xs font-medium" :class="statusClass(cap.status)">
                      {{ statusLabel(cap.status) }}
                    </span>
                  </div>
                  <p class="text-sm text-gray-500 mt-1">{{ cap.cap_id }} · {{ cap.category || '未分类' }}</p>
                  <p class="text-sm text-gray-600 mt-3 leading-6">{{ cap.description || '暂未填写能力描述' }}</p>
                  <div class="flex flex-wrap gap-2 mt-3">
                    <span v-for="tag in cap.tags || []" :key="tag" class="px-2 py-1 rounded-md bg-gray-100 text-gray-600 text-xs">
                      {{ tag }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="md:text-right shrink-0">
                <p class="text-sm font-semibold text-gray-950">{{ formatPrice(cap) }}</p>
                <p class="text-xs text-gray-500 mt-1">{{ formatNumber(cap.call_count || 0) }} 次调用</p>
              </div>
            </div>

            <div class="flex flex-wrap gap-2 mt-5 pt-4 border-t border-gray-100">
              <button
                v-if="cap.status === 'draft' || cap.status === 'rejected'"
                type="button"
                @click="submitCap(cap.cap_id)"
                class="px-3 py-1.5 bg-primary-600 text-white rounded-lg text-xs font-medium hover:bg-primary-700"
              >
                提交审核
              </button>
              <button
                v-if="cap.status === 'draft' || cap.status === 'rejected'"
                type="button"
                @click="editCap(cap)"
                class="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
              >
                编辑
              </button>
              <button
                type="button"
                @click="openUploadForm(cap)"
                class="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
              >
                上传版本包
              </button>
              <router-link
                v-if="cap.status === 'published'"
                :to="`/capability/${cap.cap_id}`"
                class="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
              >
                查看市场页
              </router-link>
            </div>
          </article>
        </div>

        <div v-else class="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <h2 class="text-lg font-semibold text-gray-950">还没有创建能力</h2>
          <p class="mt-2 text-sm text-gray-500">先创建一个能力草稿，后续可以继续补充版本包和接口配置。</p>
          <button
            type="button"
            @click="openCreateForm"
            class="mt-5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            创建第一个能力
          </button>
        </div>
      </section>

      <section v-if="activeTab === 'earnings'" class="bg-white rounded-lg border border-gray-200 p-6">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-5">
          <div>
            <h2 class="text-lg font-semibold text-gray-950">收益概览</h2>
            <p class="text-sm text-gray-500 mt-1">平台按能力调用记录统计开发者分成。</p>
          </div>
          <div class="flex gap-3">
            <input
              v-model.number="withdrawAmount"
              type="number"
              min="100"
              placeholder="提现金额"
              class="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
            />
            <button
              type="button"
              @click="doWithdraw"
              :disabled="withdrawing"
              class="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              {{ withdrawing ? '处理中...' : '申请提现' }}
            </button>
          </div>
        </div>

        <div v-if="earningsDetail.length" class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200 text-left text-gray-500">
                <th class="py-3 pr-4 font-medium">能力</th>
                <th class="py-3 pr-4 font-medium">调用</th>
                <th class="py-3 pr-4 font-medium">流水</th>
                <th class="py-3 font-medium">开发者分成</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in earningsDetail" :key="item.cap_id" class="border-b border-gray-100 last:border-0">
                <td class="py-3 pr-4 font-medium text-gray-950">{{ item.name }}</td>
                <td class="py-3 pr-4 text-gray-600">{{ formatNumber(item.total_calls || 0) }}</td>
                <td class="py-3 pr-4 text-gray-600">¥{{ (item.total_charged || 0).toFixed(2) }}</td>
                <td class="py-3 text-emerald-600 font-medium">¥{{ (item.developer_share || 0).toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="text-gray-400 text-sm">暂无收益记录。</p>
      </section>
    </div>

    <div v-if="showCreateForm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="closeCreateForm">
      <div class="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
        <h2 class="text-xl font-bold text-gray-950 mb-6">{{ editingCap ? '编辑能力' : '创建能力' }}</h2>
        <form @submit.prevent="saveCap" class="space-y-4">
          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">能力 ID</label>
              <input
                v-model.trim="capForm.cap_id"
                :disabled="!!editingCap"
                required
                pattern="[a-z0-9][a-z0-9-]*"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none disabled:bg-gray-50"
                placeholder="如 campus-cleaning-ai"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <input
                v-model.trim="capForm.name"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                placeholder="能力名称"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">一句话描述</label>
            <textarea
              v-model.trim="capForm.description"
              rows="3"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="说明这个能力解决什么问题、适合谁使用"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">详细说明</label>
            <textarea
              v-model.trim="capForm.long_description"
              rows="4"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="补充应用场景、接入方式、输入输出、注意事项等"
            />
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">分类</label>
              <select
                v-model="capForm.category"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="isp">ISP智能客服</option>
                <option value="security">AI智能监控</option>
                <option value="enterprise">企业效率</option>
                <option value="other">其他行业能力</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">标签，逗号分隔</label>
              <input
                v-model="capForm.tagsInput"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                placeholder="如 宽带,客服,工单"
              />
            </div>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">计费模式</label>
              <select
                v-model="capForm.pricing_model"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="free">免费</option>
                <option value="per_call">按次计费</option>
                <option value="subscription">包月订阅</option>
              </select>
            </div>
            <div v-if="capForm.pricing_model !== 'free'">
              <label class="block text-sm font-medium text-gray-700 mb-1">价格</label>
              <input
                v-model.number="capForm.price"
                type="number"
                min="0"
                step="0.01"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              />
            </div>
          </div>

          <div v-if="formError" class="p-3 bg-red-50 text-red-600 text-sm rounded-lg">{{ formError }}</div>

          <div class="flex gap-3 pt-2">
            <button
              type="submit"
              :disabled="saving"
              class="px-6 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              {{ saving ? '保存中...' : (editingCap ? '更新能力' : '创建草稿') }}
            </button>
            <button type="button" @click="closeCreateForm" class="px-6 py-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
              取消
            </button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="uploadCap" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="closeUploadForm">
      <div class="bg-white rounded-lg w-full max-w-lg p-6">
        <h2 class="text-xl font-bold text-gray-950 mb-2">上传版本包</h2>
        <p class="text-sm text-gray-500 mb-5">{{ uploadCap.name }} · {{ uploadCap.cap_id }}</p>
        <form @submit.prevent="uploadVersion" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">版本号</label>
            <input
              v-model.trim="uploadForm.version"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="如 1.0.0"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">更新说明</label>
            <textarea
              v-model.trim="uploadForm.changelog"
              rows="3"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="说明本版本新增或调整的内容"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">能力包</label>
            <input
              type="file"
              accept=".zip,.tar,.gz,.tgz"
              required
              class="block w-full text-sm text-gray-600 file:mr-4 file:rounded-lg file:border-0 file:bg-gray-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-gray-700 hover:file:bg-gray-200"
              @change="handlePackageChange"
            />
          </div>
          <div v-if="uploadError" class="p-3 bg-red-50 text-red-600 text-sm rounded-lg">{{ uploadError }}</div>
          <div class="flex gap-3 pt-2">
            <button
              type="submit"
              :disabled="uploading"
              class="px-6 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              {{ uploading ? '上传中...' : '上传版本' }}
            </button>
            <button type="button" @click="closeUploadForm" class="px-6 py-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { developerAPI } from '../api'

const activeTab = ref('caps')
const myCaps = ref([])
const earningsDetail = ref([])
const earningsOverview = ref({})
const showCreateForm = ref(false)
const editingCap = ref(null)
const uploadCap = ref(null)
const saving = ref(false)
const formError = ref('')
const uploadError = ref('')
const withdrawAmount = ref(0)
const withdrawing = ref(false)
const uploading = ref(false)

const capForm = reactive({
  cap_id: '',
  name: '',
  description: '',
  long_description: '',
  category: 'other',
  tagsInput: '',
  pricing_model: 'free',
  price: 0,
})

const uploadForm = reactive({
  version: '',
  changelog: '',
  package: null,
})

const tabs = [
  { key: 'caps', label: '我的能力' },
  { key: 'earnings', label: '收益' },
]

const totalCalls = computed(() => myCaps.value.reduce((sum, cap) => sum + (cap.call_count || 0), 0))
const totalEarnings = computed(() => Number(earningsOverview.value.total_earnings || 0))
const availableBalance = computed(() => Number(earningsOverview.value.available || 0))

function statusClass(status) {
  const map = {
    draft: 'bg-gray-100 text-gray-600',
    submitted: 'bg-yellow-50 text-yellow-700',
    published: 'bg-green-50 text-green-700',
    rejected: 'bg-red-50 text-red-600',
    suspended: 'bg-orange-50 text-orange-600',
  }
  return map[status] || map.draft
}

function statusLabel(status) {
  const map = {
    draft: '草稿',
    submitted: '审核中',
    published: '已上线',
    rejected: '已拒绝',
    suspended: '已暂停',
  }
  return map[status] || status || '草稿'
}

function formatNumber(n) {
  if (!n) return '0'
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function formatPrice(cap) {
  if (cap.pricing_model === 'free' || !cap.price) return '免费'
  if (cap.pricing_model === 'per_call') return `¥${cap.price}/次`
  return `¥${cap.price}/月`
}

function openCreateForm() {
  resetForm()
  showCreateForm.value = true
}

function closeCreateForm() {
  showCreateForm.value = false
  resetForm()
}

function editCap(cap) {
  editingCap.value = cap
  Object.assign(capForm, {
    cap_id: cap.cap_id,
    name: cap.name,
    description: cap.description || '',
    long_description: cap.long_description || '',
    category: cap.category || 'other',
    tagsInput: (cap.tags || []).join(', '),
    pricing_model: cap.pricing_model || 'free',
    price: cap.price || 0,
  })
  showCreateForm.value = true
}

function resetForm() {
  editingCap.value = null
  Object.assign(capForm, {
    cap_id: '',
    name: '',
    description: '',
    long_description: '',
    category: 'other',
    tagsInput: '',
    pricing_model: 'free',
    price: 0,
  })
  formError.value = ''
}

function openUploadForm(cap) {
  uploadCap.value = cap
  uploadForm.version = cap.version || '1.0.0'
  uploadForm.changelog = ''
  uploadForm.package = null
  uploadError.value = ''
}

function closeUploadForm() {
  uploadCap.value = null
  uploadForm.version = ''
  uploadForm.changelog = ''
  uploadForm.package = null
  uploadError.value = ''
}

function handlePackageChange(event) {
  uploadForm.package = event.target.files?.[0] || null
}

async function saveCap() {
  formError.value = ''
  saving.value = true
  const payload = {
    cap_id: capForm.cap_id,
    name: capForm.name,
    description: capForm.description,
    long_description: capForm.long_description,
    category: capForm.category,
    subcategory: capForm.cap_id,
    level: 'composite',
    tags: capForm.tagsInput.split(',').map(tag => tag.trim()).filter(Boolean),
    pricing_model: capForm.pricing_model,
    price: capForm.pricing_model === 'free' ? 0 : capForm.price,
  }
  try {
    if (editingCap.value) {
      await developerAPI.update(editingCap.value.cap_id, payload)
    } else {
      await developerAPI.create(payload)
    }
    closeCreateForm()
    await loadCaps()
  } catch (e) {
    formError.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function submitCap(capId) {
  try {
    await developerAPI.submit(capId)
    await loadCaps()
  } catch (e) {
    alert(e.response?.data?.detail || '提交失败')
  }
}

async function uploadVersion() {
  if (!uploadForm.package) {
    uploadError.value = '请选择能力包文件'
    return
  }
  uploading.value = true
  uploadError.value = ''
  try {
    await developerAPI.uploadVersion(uploadCap.value.cap_id, {
      version: uploadForm.version,
      changelog: uploadForm.changelog,
      package: uploadForm.package,
    })
    closeUploadForm()
    await loadCaps()
  } catch (e) {
    uploadError.value = e.response?.data?.detail || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function doWithdraw() {
  if (!withdrawAmount.value || withdrawAmount.value < 100) {
    alert('请输入不低于 100 元的提现金额')
    return
  }
  withdrawing.value = true
  try {
    await developerAPI.withdraw(withdrawAmount.value)
    alert('提现申请已提交')
    withdrawAmount.value = 0
    await loadEarnings()
  } catch (e) {
    alert(e.response?.data?.detail || '提现失败')
  } finally {
    withdrawing.value = false
  }
}

async function loadCaps() {
  try {
    const { data } = await developerAPI.capabilities()
    myCaps.value = Array.isArray(data) ? data : (data.items || [])
  } catch {
    myCaps.value = []
  }
}

async function loadEarnings() {
  try {
    const [{ data: overview }, { data: detail }] = await Promise.all([
      developerAPI.earnings(),
      developerAPI.earningsDetail(),
    ])
    earningsOverview.value = overview || {}
    earningsDetail.value = Array.isArray(detail) ? detail : (detail.items || [])
  } catch {
    earningsOverview.value = {}
    earningsDetail.value = []
  }
}

onMounted(() => {
  loadCaps()
  loadEarnings()
})
</script>
