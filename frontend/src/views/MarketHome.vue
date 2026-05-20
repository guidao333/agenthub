<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Hero (only on home) -->
    <div v-if="!selectedCat" class="bg-gradient-to-r from-primary-600 via-primary-500 to-blue-400 text-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 class="text-4xl font-bold mb-3">AI 能力市场</h1>
        <p class="text-lg text-blue-100 mb-6">发现、订阅、使用 AI Agent 能力 — 让智能触手可及</p>
        <div class="max-w-2xl relative">
          <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <input v-model="searchQuery" @keyup.enter="doSearch" class="w-full pl-12 pr-4 py-3.5 rounded-xl text-gray-900 text-base focus:outline-none focus:ring-2 focus:ring-white/50 shadow-lg" placeholder="搜索 AI 能力..." />
        </div>
      </div>
    </div>

    <!-- ══════ 首页：大分类卡片 ══════ -->
    <div v-if="!selectedCat" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Hot capabilities -->
      <section v-if="hotCaps.length" class="mb-10">
        <h3 class="text-base font-semibold text-gray-800 mb-4 flex items-center gap-2">🔥 热门能力</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          <CapabilityCard v-for="cap in hotCaps" :key="cap.cap_id" :cap="cap" @click="goDetail(cap.cap_id)" />
        </div>
      </section>

      <!-- Category Cards -->
      <h3 class="text-base font-semibold text-gray-800 mb-4">📂 能力分类</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div v-for="cat in categoryTree" :key="cat.id"
          @click="selectCat(cat)"
          class="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-lg hover:border-primary-300 transition-all cursor-pointer group">
          <div class="flex items-center gap-4 mb-3">
            <div class="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl" :style="{ backgroundColor: cat.color + '15', color: cat.color }">
              {{ cat.icon }}
            </div>
            <div class="flex-1">
              <h2 class="text-lg font-bold text-gray-900 group-hover:text-primary-600 transition-colors">{{ cat.name }}</h2>
              <p class="text-sm text-gray-500">{{ cat.count }} 个能力</p>
            </div>
            <svg class="w-5 h-5 text-gray-400 group-hover:text-primary-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          </div>
          <p class="text-sm text-gray-600 mb-4">{{ cat.description }}</p>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="sub in cat.subcategories" :key="sub.id"
              class="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
              {{ sub.name }}<span v-if="sub.count" class="text-gray-400 ml-0.5">{{ sub.count }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════ 分类详情页 ══════ -->
    <div v-if="selectedCat" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Breadcrumb -->
      <div class="flex items-center gap-2 mb-4 text-sm">
        <button @click="clearCategory" class="text-primary-600 hover:text-primary-700 font-medium">← 全部分类</button>
        <span class="text-gray-400">/</span>
        <span class="text-gray-900 font-medium">{{ currentCatInfo.icon }} {{ currentCatInfo.name }}</span>
      </div>

      <!-- Subcategory tabs -->
      <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit mb-6 flex-wrap">
        <button @click="selectedSub = ''; currentPage = 1; loadCaps()"
          class="px-4 py-2 rounded-lg text-sm font-medium transition"
          :class="!selectedSub ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
          全部 ({{ currentCatInfo.count }})
        </button>
        <button v-for="sub in activeSubcategories" :key="sub.id" @click="toggleSub(sub.id)"
          class="px-4 py-2 rounded-lg text-sm font-medium transition whitespace-nowrap"
          :class="selectedSub === sub.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
          {{ sub.name }}
          <span class="text-xs opacity-60 ml-1">{{ sub.count }}</span>
        </button>
      </div>

      <!-- Filter bar -->
      <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <h2 class="text-lg font-bold text-gray-900">
            {{ currentTitle }}
            <span v-if="total" class="text-sm font-normal text-gray-500 ml-1">共 {{ total }} 个</span>
          </h2>
          <div class="flex gap-1 ml-2">
            <button @click="toggleLevel('')"
              class="px-2.5 py-0.5 rounded-full text-xs transition"
              :class="!selectedLevel ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">全部</button>
            <button @click="toggleLevel('atomic')"
              class="px-2.5 py-0.5 rounded-full text-xs transition"
              :class="selectedLevel === 'atomic' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">⚛️ 原子能力</button>
            <button @click="toggleLevel('composite')"
              class="px-2.5 py-0.5 rounded-full text-xs transition"
              :class="selectedLevel === 'composite' ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">🧩 组合能力</button>
          </div>
        </div>
        <div class="flex gap-1">
          <button v-for="s in sorts" :key="s.value" @click="currentSort = s.value"
            class="px-3 py-1 rounded-lg text-sm transition"
            :class="currentSort === s.value ? 'bg-primary-50 text-primary-600 font-medium' : 'text-gray-500 hover:text-gray-700'">
            {{ s.label }}
          </button>
        </div>
      </div>

      <!-- Capability Grid -->
      <div v-if="caps.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <CapabilityCard v-for="cap in caps" :key="cap.cap_id" :cap="cap" @click="goDetail(cap.cap_id)" />
      </div>

      <!-- Empty -->
      <div v-else-if="!loading" class="text-center py-20 text-gray-400">
        <svg class="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <p class="text-lg">暂无符合条件的AI能力</p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex justify-center py-10">
        <div class="w-8 h-8 border-3 border-primary-200 border-t-primary-500 rounded-full animate-spin"></div>
      </div>

      <!-- Pagination -->
      <div v-if="total > pageSize" class="flex justify-center mt-8 gap-2">
        <button v-for="p in totalPages" :key="p" @click="currentPage = p"
          class="w-9 h-9 rounded-lg text-sm transition"
          :class="currentPage === p ? 'bg-primary-500 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:border-primary-300'">
          {{ p }}
        </button>
      </div>
    </div>

    <!-- 搜索结果页 -->
    <div v-if="searchQuery && !selectedCat" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-gray-900">
          搜索 "{{ searchQuery }}"
          <span v-if="total" class="text-sm font-normal text-gray-500 ml-1">共 {{ total }} 个</span>
        </h2>
        <button @click="searchQuery = ''; loadCaps()" class="text-sm text-gray-500 hover:text-gray-700">清除搜索</button>
      </div>
      <div v-if="caps.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <CapabilityCard v-for="cap in caps" :key="cap.cap_id" :cap="cap" @click="goDetail(cap.cap_id)" />
      </div>
      <div v-else-if="!loading" class="text-center py-20 text-gray-400">
        <p class="text-lg">未找到相关能力</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { marketAPI } from '../api'
import CapabilityCard from '../components/CapabilityCard.vue'

const router = useRouter()

const searchQuery = ref('')
const selectedCat = ref('')
const selectedSub = ref('')
const selectedLevel = ref('')
const currentSort = ref('call_count')
const currentPage = ref(1)
const pageSize = 20
const caps = ref([])
const hotCaps = ref([])
const categoryTree = ref([])
const total = ref(0)
const loading = ref(false)

const sorts = [
  { label: '最热', value: 'call_count' },
  { label: '最新', value: 'new' },
  { label: '评分', value: 'rating' },
]

const totalPages = computed(() => Math.ceil(total.value / pageSize))

const currentCatInfo = computed(() => {
  if (!selectedCat.value) return {}
  return categoryTree.value.find(c => c.id === selectedCat.value) || {}
})

const activeSubcategories = computed(() => currentCatInfo.value?.subcategories || [])

const currentTitle = computed(() => {
  if (selectedSub.value) {
    return activeSubcategories.value.find(s => s.id === selectedSub.value)?.name || '全部能力'
  }
  return currentCatInfo.value?.name || '全部能力'
})

async function loadCategories() {
  try {
    const { data } = await marketAPI.categories()
    categoryTree.value = data
  } catch { categoryTree.value = [] }
}

async function loadHot() {
  try {
    const { data } = await marketAPI.hot()
    hotCaps.value = data
  } catch {}
}

async function loadCaps() {
  loading.value = true
  try {
    const params = { page: currentPage.value, size: pageSize, sort: currentSort.value }
    if (searchQuery.value) params.search = searchQuery.value
    if (selectedCat.value && !selectedSub.value) params.category = selectedCat.value
    if (selectedSub.value) params.subcategory = selectedSub.value
    if (selectedLevel.value) params.level = selectedLevel.value
    const { data } = await marketAPI.list(params)
    caps.value = data.items || []
    total.value = data.total || 0
  } catch { caps.value = []; total.value = 0 }
  finally { loading.value = false }
}

function doSearch() { currentPage.value = 1; loadCaps() }

function clearCategory() {
  selectedCat.value = ''
  selectedSub.value = ''
  selectedLevel.value = ''
  caps.value = []
  total.value = 0
}

function selectCat(cat) {
  selectedCat.value = cat.id
  selectedSub.value = ''
  selectedLevel.value = ''
  currentPage.value = 1
  loadCaps()
}

function toggleSub(subId) {
  selectedSub.value = selectedSub.value === subId ? '' : subId
  currentPage.value = 1
  loadCaps()
}

function toggleLevel(level) {
  selectedLevel.value = selectedLevel.value === level ? '' : level
  currentPage.value = 1
  loadCaps()
}

function goDetail(capId) { router.push({ name: 'capability', params: { capId } }) }

watch([currentSort], () => { currentPage.value = 1; if (selectedCat.value) loadCaps() })
watch(currentPage, () => { if (selectedCat.value) loadCaps() })

onMounted(() => {
  loadCategories()
  loadHot()
})
</script>
