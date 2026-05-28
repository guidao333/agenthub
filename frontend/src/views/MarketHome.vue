<template>
  <div class="min-h-screen bg-gray-50">
    <section class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-10">
        <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div class="max-w-3xl">
            <p class="text-sm font-semibold text-primary-600">AgentHub</p>
            <h1 class="mt-2 text-3xl lg:text-4xl font-bold tracking-tight text-gray-950">
              AI能力市场
            </h1>
            <p class="mt-3 text-base text-gray-600 leading-7">
              订阅可落地的行业AI能力，也欢迎开发者持续训练、上传更多能力模块。
            </p>
          </div>

          <div class="w-full lg:w-[420px]">
            <div class="relative">
              <input
                v-model.trim="searchQuery"
                @keyup.enter="doSearch"
                class="w-full h-12 rounded-lg border border-gray-300 bg-white px-4 pr-24 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500"
                placeholder="搜索能力，如 智能客服、AI监控"
              />
              <button
                type="button"
                class="absolute right-1.5 top-1.5 h-9 px-4 rounded-md bg-primary-600 text-white text-sm font-medium hover:bg-primary-700"
                @click="doSearch"
              >
                搜索
              </button>
            </div>
          </div>
        </div>

        <div class="mt-6 flex gap-2 overflow-x-auto pb-1">
          <button
            v-for="chip in categoryChips"
            :key="chip.id"
            type="button"
            class="shrink-0 rounded-full border px-4 py-2 text-sm transition"
            :class="selectedCat === chip.id ? 'border-primary-600 bg-primary-50 text-primary-700 font-medium' : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:text-gray-900'"
            @click="selectChip(chip)"
          >
            {{ chip.name }}
          </button>
        </div>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-5">
        <div>
          <p class="text-sm text-gray-500">{{ listHint }}</p>
          <h2 class="mt-1 text-2xl font-bold text-gray-950">{{ listTitle }}</h2>
        </div>
        <RouterLink
          :to="{ path: '/register', query: { role: 'developer' } }"
          class="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-primary-300 hover:text-primary-700"
        >
          开发者入驻 / 上传能力
        </RouterLink>
      </div>

      <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="i in 6" :key="i" class="h-56 rounded-lg border border-gray-200 bg-white animate-pulse"></div>
      </div>

      <div v-else-if="displayCaps.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <CapabilityCard
          v-for="cap in displayCaps"
          :key="cap.cap_id"
          :cap="cap"
          @click="goDetail(cap.cap_id)"
        />
      </div>

      <div v-else class="rounded-lg border border-gray-200 bg-white p-10 text-center">
        <h3 class="text-lg font-semibold text-gray-950">暂时没有找到匹配的能力</h3>
        <p class="mt-2 text-sm text-gray-500">换个关键词，或先查看全部能力模块。</p>
        <button
          type="button"
          class="mt-5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          @click="resetFilters"
        >
          查看全部能力
        </button>
      </div>
    </section>

    <section class="border-t border-gray-200 bg-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-base font-semibold text-gray-950">开放能力生态</h2>
            <p class="mt-1 text-sm text-gray-600">
              后续平台将支持更多开发者训练、发布、运营自己的行业能力模块。
            </p>
          </div>
          <RouterLink
            :to="{ path: '/register', query: { role: 'developer' } }"
            class="inline-flex items-center justify-center rounded-lg bg-gray-950 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
          >
            申请成为开发者
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { marketAPI } from '../api'
import CapabilityCard from '../components/CapabilityCard.vue'

const router = useRouter()

const searchQuery = ref('')
const selectedCat = ref('')
const currentSort = ref('call_count')
const currentPage = ref(1)
const pageSize = 24
const caps = ref([])
const hotCaps = ref([])
const categoryTree = ref([])
const loading = ref(false)

const categoryChips = computed(() => {
  const chips = [{ id: '', name: '全部' }]
  const apiChips = categoryTree.value.slice(0, 6).map(cat => ({
    id: cat.id,
    name: cat.name || cat.title || cat.id,
  }))
  if (apiChips.length) {
    return chips.concat(apiChips)
  }
  return chips.concat([
    { id: 'isp', name: 'ISP智能客服' },
    { id: 'vision', name: 'AI智能监控' },
    { id: 'more', name: '更多行业能力' },
  ])
})

const displayCaps = computed(() => {
  if (searchQuery.value || selectedCat.value) return caps.value
  if (!hotCaps.value.length) return caps.value
  const fullById = new Map(caps.value.map(cap => [cap.cap_id, cap]))
  return hotCaps.value.map(cap => ({ ...cap, ...(fullById.get(cap.cap_id) || {}) }))
})

const listTitle = computed(() => {
  if (searchQuery.value) return `搜索：${searchQuery.value}`
  const cat = categoryChips.value.find(item => item.id === selectedCat.value)
  if (cat?.id) return cat.name
  return '推荐能力模块'
})

const listHint = computed(() => {
  if (searchQuery.value || selectedCat.value) return '筛选结果'
  return '简洁浏览，点击卡片查看完整能力介绍'
})

async function loadCategories() {
  try {
    const { data } = await marketAPI.categories()
    categoryTree.value = Array.isArray(data) ? data : []
  } catch {
    categoryTree.value = []
  }
}

async function loadHot() {
  try {
    const { data } = await marketAPI.hot()
    hotCaps.value = Array.isArray(data) ? data : []
  } catch {
    hotCaps.value = []
  }
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
    if (selectedCat.value) params.category = selectedCat.value
    const { data } = await marketAPI.list(params)
    caps.value = Array.isArray(data.items) ? data.items : []
  } catch {
    caps.value = []
  } finally {
    loading.value = false
  }
}

function doSearch() {
  selectedCat.value = ''
  currentPage.value = 1
  loadCaps()
}

function selectChip(chip) {
  searchQuery.value = ''
  selectedCat.value = chip.id
  currentPage.value = 1
  if (chip.id) {
    loadCaps()
  } else {
    loadCaps()
  }
}

function resetFilters() {
  searchQuery.value = ''
  selectedCat.value = ''
  currentPage.value = 1
  loadCaps()
}

function goDetail(capId) {
  router.push({ name: 'capability', params: { capId } })
}

watch(currentSort, () => {
  currentPage.value = 1
  loadCaps()
})

onMounted(async () => {
  await Promise.all([loadCategories(), loadHot(), loadCaps()])
})
</script>
