<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <h1 class="text-2xl font-bold text-gray-900 mb-4">管理后台</h1>

    <!-- Stats Overview -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
      <div v-for="s in statCards" :key="s.label" class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 mb-1">{{ s.label }}</p>
        <p class="text-xl font-bold" :class="s.color || 'text-gray-900'">{{ s.value }}</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit mb-6 flex-wrap">
      <button v-for="tab in tabs" :key="tab.key" @click="switchTab(tab.key)"
        class="px-4 py-2 rounded-lg text-sm font-medium transition"
        :class="activeTab === tab.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
        {{ tab.icon }} {{ tab.label }}
        <span v-if="tab.badge" class="ml-1 px-1.5 py-0.5 bg-red-500 text-white text-xs rounded-full">{{ tab.badge }}</span>
      </button>
    </div>

    <!-- ══════ 能力管理 ══════ -->
    <div v-if="activeTab === 'caps'">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <input v-model="capSearch" @keyup.enter="loadCaps" class="px-3 py-1.5 border rounded-lg text-sm w-48" placeholder="搜索能力..." />
          <select v-model="capStatusFilter" @change="loadCaps" class="px-3 py-1.5 border rounded-lg text-sm">
            <option value="">全部状态</option>
            <option value="published">已上架</option>
            <option value="draft">草稿</option>
            <option value="submitted">待审核</option>
            <option value="suspended">已暂停</option>
          </select>
          <select v-model="capCatFilter" @change="loadCaps" class="px-3 py-1.5 border rounded-lg text-sm">
            <option value="">全部分类</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.icon }} {{ c.name }}</option>
          </select>
        </div>
        <button @click="openCapForm()" class="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700">
          + 创建能力
        </button>
      </div>
      <table class="w-full text-sm bg-white rounded-xl border border-gray-200 overflow-hidden">
        <thead class="bg-gray-50">
          <tr>
            <th class="text-left px-4 py-2 text-gray-500 font-medium">名称</th>
            <th class="text-left px-4 py-2 text-gray-500 font-medium">分类</th>
            <th class="text-left px-4 py-2 text-gray-500 font-medium">层级</th>
            <th class="text-left px-4 py-2 text-gray-500 font-medium">定价</th>
            <th class="text-left px-4 py-2 text-gray-500 font-medium">调用</th>
            <th class="text-left px-4 py-2 text-gray-500 font-medium">状态</th>
            <th class="text-left px-4 py-2 text-gray-500 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="cap in caps" :key="cap.cap_id" class="border-t border-gray-100 hover:bg-gray-50">
            <td class="px-4 py-2">
              <div class="font-medium text-gray-900">{{ cap.name }}</div>
              <div class="text-xs text-gray-400">{{ cap.cap_id }}</div>
            </td>
            <td class="px-4 py-2 text-gray-600">{{ cap.category }}</td>
            <td class="px-4 py-2">
              <span class="px-2 py-0.5 text-xs rounded-full" :class="cap.level === 'composite' ? 'bg-purple-50 text-purple-600' : 'bg-green-50 text-green-600'">
                {{ cap.level === 'composite' ? '组合' : '原子' }}
              </span>
            </td>
            <td class="px-4 py-2">
              <input v-model="cap._editPrice" @blur="savePrice(cap)" @keyup.enter="savePrice(cap)"
                class="w-20 px-2 py-1 border rounded text-sm text-right" />
              <select v-model="cap._editModel" @change="savePrice(cap)" class="ml-1 px-1 py-1 border rounded text-xs">
                <option value="per_call">/次</option>
                <option value="monthly">/月</option>
                <option value="free">免费</option>
              </select>
            </td>
            <td class="px-4 py-2 text-gray-600">{{ fmtNum(cap.call_count) }}</td>
            <td class="px-4 py-2">
              <span class="px-2 py-0.5 text-xs rounded-full" :class="statusClass(cap.status)">{{ statusLabel(cap.status) }}</span>
            </td>
            <td class="px-4 py-2">
              <div class="flex gap-1">
                <button @click="openCapForm(cap)" class="px-2 py-1 text-xs text-primary-600 hover:bg-primary-50 rounded">编辑</button>
                <button v-if="cap.status === 'published'" @click="toggleCapStatus(cap, 'suspended')" class="px-2 py-1 text-xs text-yellow-600 hover:bg-yellow-50 rounded">暂停</button>
                <button v-if="cap.status === 'suspended'" @click="toggleCapStatus(cap, 'published')" class="px-2 py-1 text-xs text-green-600 hover:bg-green-50 rounded">恢复</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="caps.length === 0" class="text-center py-10 text-gray-400">暂无能力数据</div>
    </div>

    <!-- ══════ 分类管理 ══════ -->
    <div v-if="activeTab === 'cats'">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">分类管理</h2>
        <button @click="openCatForm()" class="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium">+ 添加分类</button>
      </div>
      <div v-for="cat in categories" :key="cat.id" class="bg-white rounded-xl border border-gray-200 p-4 mb-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="text-2xl">{{ cat.icon }}</span>
            <div>
              <h3 class="font-semibold text-gray-900">{{ cat.name }}</h3>
              <p class="text-sm text-gray-500">{{ cat.description }} · {{ cat.count }}个能力</p>
            </div>
            <span class="w-5 h-5 rounded-full border" :style="{ backgroundColor: cat.color }"></span>
          </div>
          <div class="flex gap-1">
            <button @click="openCatForm(cat)" class="px-3 py-1 text-sm text-primary-600 hover:bg-primary-50 rounded">编辑</button>
            <button @click="addSubCategory(cat)" class="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded">+子分类</button>
            <button @click="deleteCat(cat.id, cat.name)" class="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded">删除</button>
          </div>
        </div>
        <div class="flex flex-wrap gap-2 mt-3 ml-10">
          <span v-for="sub in cat.subcategories" :key="sub.id"
            class="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded-full flex items-center gap-2">
            {{ sub.name }}
            <button @click="deleteCat(sub.id, sub.name)" class="text-gray-400 hover:text-red-500 text-xs">✕</button>
          </span>
        </div>
      </div>
    </div>

    <!-- ══════ 审核 ══════ -->
    <div v-if="activeTab === 'reviews'">
      <div v-if="pendingReviews.length" class="space-y-3">
        <div v-for="cap in pendingReviews" :key="cap.cap_id" class="bg-white rounded-xl border border-gray-200 p-4">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-semibold text-gray-900">{{ cap.name }}</h3>
              <p class="text-sm text-gray-600 mt-1">{{ cap.description }}</p>
              <div class="flex gap-3 mt-2 text-xs text-gray-500">
                <span>开发者: {{ cap.developer }}</span>
                <span>版本: {{ cap.version }}</span>
                <span>定价: {{ cap.pricing_model }} ¥{{ cap.price }}</span>
              </div>
            </div>
            <div class="flex gap-2">
              <button @click="approveCap(cap.cap_id)" class="px-4 py-2 bg-green-500 text-white rounded-lg text-sm">通过</button>
              <button @click="rejectCap(cap.cap_id)" class="px-4 py-2 bg-red-500 text-white rounded-lg text-sm">拒绝</button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-16 text-gray-400">暂无待审核能力</div>
    </div>

    <!-- ══════ 用户 ══════ -->
    <div v-if="activeTab === 'users'">
      <table class="w-full text-sm bg-white rounded-xl border border-gray-200 overflow-hidden">
        <thead class="bg-gray-50">
          <tr>
            <th class="text-left px-4 py-2 text-gray-500">用户名</th>
            <th class="text-left px-4 py-2 text-gray-500">邮箱</th>
            <th class="text-left px-4 py-2 text-gray-500">角色</th>
            <th class="text-left px-4 py-2 text-gray-500">余额</th>
            <th class="text-left px-4 py-2 text-gray-500">状态</th>
            <th class="text-left px-4 py-2 text-gray-500">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-t border-gray-100">
            <td class="px-4 py-2 font-medium">{{ u.username }}</td>
            <td class="px-4 py-2 text-gray-600">{{ u.email }}</td>
            <td class="px-4 py-2">
              <span class="px-2 py-0.5 text-xs rounded-full" :class="roleClass(u.role)">{{ {customer:'客户',developer:'开发者',admin:'管理员'}[u.role] }}</span>
            </td>
            <td class="px-4 py-2 text-gray-600">¥{{ (u.balance || 0).toFixed(2) }}</td>
            <td class="px-4 py-2">
              <span class="px-2 py-0.5 text-xs rounded-full" :class="u.status==='active'?'bg-green-50 text-green-600':'bg-gray-100 text-gray-500'">{{ u.status === 'active' ? '正常' : u.status }}</span>
            </td>
            <td class="px-4 py-2">
              <button v-if="u.role !== 'admin'" @click="toggleUser(u)" class="px-2 py-1 text-xs rounded" :class="u.status === 'active' ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'">
                {{ u.status === 'active' ? '封禁' : '解封' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ══════ 财务 ══════ -->
    <div v-if="activeTab === 'finance'">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        <div class="bg-white rounded-xl border p-4"><p class="text-xs text-gray-500">总收入</p><p class="text-xl font-bold text-green-600">¥{{ (finance.total_revenue||0).toFixed(2) }}</p></div>
        <div class="bg-white rounded-xl border p-4"><p class="text-xs text-gray-500">本月收入</p><p class="text-xl font-bold text-blue-600">¥{{ (finance.month_revenue||0).toFixed(2) }}</p></div>
        <div class="bg-white rounded-xl border p-4"><p class="text-xs text-gray-500">平台利润(30%)</p><p class="text-xl font-bold text-amber-600">¥{{ (finance.platform_cut||0).toFixed(2) }}</p></div>
        <div class="bg-white rounded-xl border p-4"><p class="text-xs text-gray-500">待提现</p><p class="text-xl font-bold text-purple-600">¥{{ (finance.pending_withdrawals||0).toFixed(2) }}</p></div>
      </div>
    </div>

    <!-- ══════ Modal: 创建/编辑能力 ══════ -->
    <div v-if="showCapForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showCapForm=false">
      <div class="bg-white rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <h2 class="text-lg font-bold mb-4">{{ editingCap ? '编辑能力' : '创建能力' }}</h2>
        <div class="space-y-3">
          <div>
            <label class="text-sm text-gray-600">能力ID</label>
            <input v-model="capForm.cap_id" :disabled="!!editingCap" class="w-full px-3 py-2 border rounded-lg text-sm" placeholder="如 isp-lfradius" />
          </div>
          <div>
            <label class="text-sm text-gray-600">名称</label>
            <input v-model="capForm.name" class="w-full px-3 py-2 border rounded-lg text-sm" placeholder="LFRADIUS计费系统" />
          </div>
          <div>
            <label class="text-sm text-gray-600">描述</label>
            <textarea v-model="capForm.description" rows="3" class="w-full px-3 py-2 border rounded-lg text-sm" placeholder="能力描述..."></textarea>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-sm text-gray-600">分类</label>
              <select v-model="capForm.category" class="w-full px-3 py-2 border rounded-lg text-sm">
                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.icon }} {{ c.name }}</option>
              </select>
            </div>
            <div>
              <label class="text-sm text-gray-600">子分类</label>
              <select v-model="capForm.subcategory" class="w-full px-3 py-2 border rounded-lg text-sm">
                <option value="">无</option>
                <option v-for="s in subCatsForForm" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-sm text-gray-600">层级</label>
              <select v-model="capForm.level" class="w-full px-3 py-2 border rounded-lg text-sm">
                <option value="atomic">原子能力</option>
                <option value="composite">组合能力</option>
              </select>
            </div>
            <div>
              <label class="text-sm text-gray-600">计费方式</label>
              <select v-model="capForm.pricing_model" class="w-full px-3 py-2 border rounded-lg text-sm">
                <option value="per_call">按次</option>
                <option value="monthly">按月</option>
                <option value="free">免费</option>
              </select>
            </div>
          </div>
          <div>
            <label class="text-sm text-gray-600">价格</label>
            <input v-model.number="capForm.price" type="number" step="0.01" class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label class="text-sm text-gray-600">标签 (逗号分隔)</label>
            <input v-model="capForm.tagsStr" class="w-full px-3 py-2 border rounded-lg text-sm" placeholder="计费,LFRADIUS,账单" />
          </div>
        </div>
        <div class="flex justify-end gap-2 mt-5">
          <button @click="showCapForm=false" class="px-4 py-2 text-gray-600 border rounded-lg text-sm">取消</button>
          <button @click="saveCap" class="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium">保存</button>
        </div>
      </div>
    </div>

    <!-- ══════ Modal: 创建/编辑分类 ══════ -->
    <div v-if="showCatForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showCatForm=false">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md">
        <h2 class="text-lg font-bold mb-4">{{ editingCat ? '编辑分类' : (catForm.parent_id ? '添加子分类' : '添加分类') }}</h2>
        <div class="space-y-3">
          <div>
            <label class="text-sm text-gray-600">分类ID</label>
            <input v-model="catForm.cat_id" :disabled="!!editingCat" class="w-full px-3 py-2 border rounded-lg text-sm" placeholder="如 isp-billing" />
          </div>
          <div>
            <label class="text-sm text-gray-600">名称</label>
            <input v-model="catForm.name" class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div v-if="!catForm.parent_id">
            <label class="text-sm text-gray-600">图标</label>
            <input v-model="catForm.icon" class="w-full px-3 py-2 border rounded-lg text-sm" placeholder="📡" />
          </div>
          <div v-if="!catForm.parent_id">
            <label class="text-sm text-gray-600">颜色</label>
            <div class="flex items-center gap-2">
              <input v-model="catForm.color" type="color" class="w-10 h-10 rounded cursor-pointer" />
              <input v-model="catForm.color" class="px-3 py-2 border rounded-lg text-sm flex-1" />
            </div>
          </div>
          <div>
            <label class="text-sm text-gray-600">描述</label>
            <input v-model="catForm.description" class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
        </div>
        <div class="flex justify-end gap-2 mt-5">
          <button @click="showCatForm=false" class="px-4 py-2 text-gray-600 border rounded-lg text-sm">取消</button>
          <button @click="saveCat" class="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { adminAPI, marketAPI } from '../api'

const activeTab = ref('caps')
const caps = ref([])
const categories = ref([])
const pendingReviews = ref([])
const users = ref([])
const finance = ref({})
const stats = ref({})
const capSearch = ref('')
const capStatusFilter = ref('')
const capCatFilter = ref('')

const showCapForm = ref(false)
const editingCap = ref(null)
const capForm = ref({ cap_id:'', name:'', description:'', category:'', subcategory:'', level:'atomic', pricing_model:'monthly', price:0, tagsStr:'' })

const showCatForm = ref(false)
const editingCat = ref(null)
const catForm = ref({ cat_id:'', name:'', icon:'', color:'#6B7280', description:'', parent_id:0 })

const tabs = computed(() => [
  { key:'caps', icon:'📦', label:'能力管理' },
  { key:'cats', icon:'📂', label:'分类管理' },
  { key:'reviews', icon:'✅', label:'审核', badge: pendingReviews.value.length || undefined },
  { key:'users', icon:'👥', label:'用户' },
  { key:'finance', icon:'💰', label:'财务' },
])

const statCards = computed(() => [
  { label:'已上架能力', value: stats.value.published || 0, color:'text-primary-600' },
  { label:'总用户', value: stats.value.users || 0, color:'text-blue-600' },
  { label:'总调用', value: fmtNum(stats.value.total_calls || 0), color:'text-green-600' },
  { label:'待审核', value: stats.value.reviews_pending || 0, color:'text-yellow-600' },
  { label:'总收入', value: '¥'+(finance.value.total_revenue||0).toFixed(2), color:'text-amber-600' },
])

const subCatsForForm = computed(() => {
  const cat = categories.value.find(c => c.id === capForm.value.category)
  return cat?.subcategories || []
})

// ── Loaders ──
async function loadCaps() {
  try {
    const params = { page:1, size:100 }
    if (capSearch.value) params.search = capSearch.value
    if (capStatusFilter.value) params.status = capStatusFilter.value
    if (capCatFilter.value) params.category = capCatFilter.value
    const { data } = await adminAPI.listCaps(params)
    caps.value = (data.items || []).map(c => ({ ...c, _editPrice: c.price, _editModel: c.pricing_model }))
  } catch {}
}

async function loadCategories() {
  try {
    const { data } = await adminAPI.categories()
    categories.value = data
  } catch {}
}

async function loadPending() {
  try { const { data } = await adminAPI.pendingReviews(); pendingReviews.value = Array.isArray(data) ? data : (data.items || []) } catch {}
}

async function loadUsers() {
  try { const { data } = await adminAPI.users(); users.value = data.items || [] } catch {}
}

async function loadFinance() {
  try { const { data } = await adminAPI.finance(); finance.value = data } catch {}
}

async function loadStats() {
  try { const { data } = await adminAPI.stats(); stats.value = data } catch {}
}

// ── Tab switch ──
function switchTab(key) {
  activeTab.value = key
}

// ── Capability actions ──
function openCapForm(cap) {
  if (cap) {
    editingCap.value = cap
    capForm.value = { ...cap, tagsStr: (cap.tags || []).join(',') }
  } else {
    editingCap.value = null
    capForm.value = { cap_id:'', name:'', description:'', category: categories.value[0]?.id || '', subcategory:'', level:'atomic', pricing_model:'monthly', price:0, tagsStr:'' }
  }
  showCapForm.value = true
}

async function saveCap() {
  const f = capForm.value
  const payload = {
    cap_id: f.cap_id, name: f.name, description: f.description,
    category: f.category, subcategory: f.subcategory, level: f.level,
    pricing_model: f.pricing_model, price: f.price,
    tags: f.tagsStr ? f.tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [],
  }
  try {
    if (editingCap.value) {
      await adminAPI.updateCap(f.cap_id, payload)
    } else {
      await adminAPI.createCap(payload)
    }
    showCapForm.value = false
    loadCaps()
    loadCategories()
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function savePrice(cap) {
  if (cap._editPrice === cap.price && cap._editModel === cap.pricing_model) return
  try {
    await adminAPI.updatePricing(cap.cap_id, {
      price: cap._editModel === 'free' ? 0 : cap._editPrice,
      pricing_model: cap._editModel === 'free' ? 'free' : cap._editModel,
    })
    cap.price = cap._editPrice
    cap.pricing_model = cap._editModel
  } catch {}
}

async function toggleCapStatus(cap, newStatus) {
  try {
    await adminAPI.updateCap(cap.cap_id, { status: newStatus })
    cap.status = newStatus
    loadCategories()
  } catch {}
}

// ── Category actions ──
function openCatForm(cat) {
  if (cat) {
    editingCat.value = cat
    catForm.value = { cat_id: cat.id, name: cat.name, icon: cat.icon, color: cat.color, description: cat.description, parent_id: 0 }
  } else {
    editingCat.value = null
    catForm.value = { cat_id:'', name:'', icon:'📦', color:'#6B7280', description:'', parent_id: 0 }
  }
  showCatForm.value = true
}

function addSubCategory(cat) {
  editingCat.value = null
  catForm.value = { cat_id:'', name:'', icon:'', color:'#6B7280', description:'', parent_id: cat.db_id }
  showCatForm.value = true
}

async function saveCat() {
  const f = catForm.value
  try {
    if (editingCat.value) {
      await adminAPI.updateCategory(f.cat_id, { name: f.name, icon: f.icon, color: f.color, description: f.description })
    } else {
      await adminAPI.createCategory(f)
    }
    showCatForm.value = false
    loadCategories()
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function deleteCat(catId, name) {
  if (!confirm(`确定删除分类"${name}"？`)) return
  try {
    await adminAPI.deleteCategory(catId)
    loadCategories()
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

// ── Review actions ──
async function approveCap(capId) {
  try { await adminAPI.approve(capId); loadPending(); loadCaps() } catch (e) { alert(e.response?.data?.detail) }
}
async function rejectCap(capId) {
  try { await adminAPI.reject(capId); loadPending() } catch (e) { alert(e.response?.data?.detail) }
}

// ── User actions ──
async function toggleUser(u) {
  try {
    if (u.status === 'active') await adminAPI.suspendUser(u.id)
    else await adminAPI.activateUser(u.id)
    loadUsers()
  } catch {}
}

// ── Helpers ──
function statusClass(s) {
  const m = { published:'bg-green-50 text-green-600', draft:'bg-gray-100 text-gray-500', submitted:'bg-yellow-50 text-yellow-600', rejected:'bg-red-50 text-red-600', suspended:'bg-orange-50 text-orange-600' }
  return m[s] || 'bg-gray-100 text-gray-500'
}
function statusLabel(s) {
  const m = { published:'已上架', draft:'草稿', submitted:'待审核', rejected:'已拒绝', suspended:'已暂停' }
  return m[s] || s
}
function roleClass(r) {
  const m = { customer:'bg-blue-50 text-blue-600', developer:'bg-purple-50 text-purple-600', admin:'bg-red-50 text-red-600' }
  return m[r] || 'bg-gray-100 text-gray-600'
}
function fmtNum(n) { if (!n) return '0'; if (n >= 10000) return (n/10000).toFixed(1)+'万'; return String(n) }

onMounted(() => {
  loadCaps()
  loadCategories()
  loadPending()
  loadUsers()
  loadFinance()
  loadStats()
})
</script>
