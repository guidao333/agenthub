<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Hero -->
    <div class="bg-gradient-to-r from-primary-600 via-primary-500 to-blue-400 text-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h1 class="text-4xl font-bold mb-3">AI 能力市场</h1>
        <p class="text-lg text-blue-100 mb-8">发现、订阅、使用 AI Agent 能力 — 让智能触手可及</p>
        <div class="max-w-2xl relative">
          <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <input v-model="searchQuery" @keyup.enter="doSearch" class="w-full pl-12 pr-4 py-3.5 rounded-xl text-gray-900 text-base focus:outline-none focus:ring-2 focus:ring-white/50 shadow-lg" placeholder="搜索 AI 能力..." />
        </div>
      </div>
    </div>

    <!-- Categories -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-6">
      <div class="bg-white rounded-xl shadow-md p-4 flex gap-2 overflow-x-auto">
        <button v-for="cat in categories" :key="cat.name" @click="selectCategory(cat)"
          class="px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition"
          :class="selectedCategory === cat.name ? 'bg-primary-500 text-white' : cat.available ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-gray-50 text-gray-400 cursor-not-allowed'">
          {{ cat.name }}
          <span v-if="!cat.available" class="text-xs ml-1 opacity-60">即将开放</span>
        </button>
      </div>
    </div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Hot capabilities -->
      <section v-if="hotCaps.length && !searchQuery && !selectedCategory" class="mb-10">
        <h2 class="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clip-rule="evenodd"/></svg>
          热门能力
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <CapabilityCard v-for="cap in hotCaps" :key="cap.cap_id" :cap="cap" @click="goDetail(cap.cap_id)" />
        </div>
      </section>

      <!-- Sort tabs -->
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-bold text-gray-900">
          {{ selectedCategory || '全部能力' }}
          <span v-if="total" class="text-sm font-normal text-gray-500 ml-2">共 {{ total }} 个</span>
        </h2>
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
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { marketAPI } from '../api'
import CapabilityCard from '../components/CapabilityCard.vue'

const router = useRouter()

const searchQuery = ref('')
const selectedCategory = ref('')
const currentSort = ref('call_count')
const currentPage = ref(1)
const pageSize = 20
const caps = ref([])
const hotCaps = ref([])
const categories = ref([])
const total = ref(0)
const loading = ref(false)

const sorts = [
  { label: '最热', value: 'call_count' },
  { label: '最新', value: 'created_at' },
  { label: '评分', value: 'avg_rating' },
]

const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function loadCategories() {
  try {
    const { data } = await marketAPI.categories()
    categories.value = data
  } catch { categories.value = [{ name: 'ISP网络', available: true, subcategories: [] }] }
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
    const params = {
      page: currentPage.value,
      size: pageSize,
      sort: currentSort.value,
    }
    if (searchQuery.value) params.search = searchQuery.value
    if (selectedCategory.value) params.category = selectedCategory.value
    const { data } = await marketAPI.list(params)
    caps.value = data.items || []
    total.value = data.total || 0
  } catch {
    caps.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function doSearch() {
  currentPage.value = 1
  loadCaps()
}

function selectCategory(cat) {
  if (!cat.available) return
  selectedCategory.value = selectedCategory.value === cat.name ? '' : cat.name
  currentPage.value = 1
  loadCaps()
}

function goDetail(capId) {
  router.push({ name: 'capability', params: { capId } })
}

watch([currentSort], () => { currentPage.value = 1; loadCaps() })
watch(currentPage, loadCaps)

onMounted(() => {
  loadCategories()
  loadHot()
  loadCaps()
})
</script>
