<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div v-if="loading" class="flex justify-center py-20">
      <div class="w-8 h-8 border-3 border-primary-200 border-t-primary-500 rounded-full animate-spin"></div>
    </div>

    <div v-else-if="cap" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Main Content -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Header -->
        <div>
          <button @click="$router.back()" class="text-sm text-gray-500 hover:text-gray-700 mb-4 flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
            返回市场
          </button>
          <div class="flex items-start gap-4">
            <div class="w-16 h-16 rounded-2xl bg-primary-50 text-primary-600 flex items-center justify-center text-2xl font-bold shrink-0">
              {{ cap.name.charAt(0) }}
            </div>
            <div class="flex-1">
              <h1 class="text-2xl font-bold text-gray-900">{{ cap.name }}</h1>
              <p class="text-gray-500 mt-1">by {{ cap.developer_name || '未知开发者' }} · {{ cap.category }}</p>
              <div class="flex items-center gap-4 mt-2">
                <span v-if="cap.avg_rating" class="flex items-center gap-1 text-amber-500">
                  <svg class="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                  {{ cap.avg_rating?.toFixed(1) || '-' }}
                </span>
                <span class="text-gray-500 text-sm">{{ cap.call_count || 0 }} 次调用</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Tags -->
        <div class="flex flex-wrap gap-2">
          <span v-if="cap.level" class="px-3 py-1 text-sm rounded-full" :class="cap.level === 'atomic' ? 'bg-green-50 text-green-700' : 'bg-purple-50 text-purple-700'">
            {{ cap.level === 'atomic' ? '⚛️ 原子能力' : '🧩 组合能力' }}
          </span>
          <span v-for="tag in (cap.tags || [])" :key="tag" class="px-3 py-1 bg-primary-50 text-primary-600 text-sm rounded-full">{{ tag }}</span>
        </div>

        <!-- Dependencies -->
        <div v-if="cap.dependencies && cap.dependencies.length" class="bg-purple-50 rounded-xl p-4">
          <h3 class="text-sm font-semibold text-purple-800 mb-2">🧩 编排的原子能力</h3>
          <div class="flex flex-wrap gap-2">
            <span v-for="dep in cap.dependencies" :key="dep" class="px-3 py-1 bg-white text-purple-600 text-sm rounded-full border border-purple-200">{{ dep }}</span>
          </div>
        </div>

        <!-- Description -->
        <div class="bg-white rounded-xl border border-gray-200 p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-3">能力描述</h2>
          <p class="text-gray-700 leading-relaxed whitespace-pre-wrap">{{ cap.description }}</p>
        </div>

        <!-- Reviews -->
        <div class="bg-white rounded-xl border border-gray-200 p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">用户评价 ({{ reviews.length }})</h2>
          <div v-if="reviews.length" class="space-y-4">
            <div v-for="review in reviews" :key="review.id" class="border-b border-gray-100 pb-4 last:border-0">
              <div class="flex items-center justify-between mb-1">
                <span class="font-medium text-gray-800">{{ review.username || '匿名用户' }}</span>
                <span class="text-xs text-gray-400">{{ formatDate(review.created_at) }}</span>
              </div>
              <div v-if="review.rating" class="flex items-center gap-0.5 mb-1">
                <svg v-for="i in 5" :key="i" class="w-3.5 h-3.5" :class="i <= review.rating ? 'text-amber-400 fill-current' : 'text-gray-200 fill-current'" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
              </div>
              <p class="text-sm text-gray-600">{{ review.comment }}</p>
            </div>
          </div>
          <p v-else class="text-gray-400 text-sm">暂无评价</p>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-6">
        <!-- Pricing Card -->
        <div class="bg-white rounded-xl border border-gray-200 p-6 sticky top-20">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">定价</h3>
          <div class="text-3xl font-bold mb-1" :class="cap.pricing_model === 'free' ? 'text-green-600' : 'text-gray-900'">
            {{ formatPrice(cap) }}
          </div>
          <p class="text-sm text-gray-500 mb-6">{{ pricingLabel(cap.pricing_model) }}</p>

          <button v-if="isSubscribed" disabled
            class="w-full py-2.5 bg-green-50 text-green-600 rounded-xl font-medium cursor-default">
            ✓ 已订阅
          </button>
          <button v-else @click="handleSubscribe"
            :disabled="subscribing"
            class="w-full py-2.5 bg-primary-500 text-white rounded-xl font-medium hover:bg-primary-600 disabled:opacity-50 transition">
            {{ subscribing ? '订阅中...' : '立即订阅' }}
          </button>

          <!-- Try it -->
          <button v-if="isSubscribed" @click="startChat"
            class="w-full mt-3 py-2.5 border border-primary-500 text-primary-600 rounded-xl font-medium hover:bg-primary-50 transition">
            开始对话
          </button>
        </div>

        <!-- Info -->
        <div class="bg-white rounded-xl border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-3">能力信息</h3>
          <dl class="space-y-3 text-sm">
            <div class="flex justify-between">
              <dt class="text-gray-500">能力层级</dt>
              <dd class="font-medium" :class="cap.level === 'atomic' ? 'text-green-600' : 'text-purple-600'">
                {{ cap.level === 'atomic' ? '⚛️ 原子能力' : '🧩 组合能力' }}
              </dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">分类</dt>
              <dd class="text-gray-900 font-medium">{{ cap.category || '-' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">开发者</dt>
              <dd class="text-gray-900 font-medium">{{ cap.developer_name || '-' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">计费模式</dt>
              <dd class="text-gray-900 font-medium">{{ pricingLabel(cap.pricing_model) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">调用次数</dt>
              <dd class="text-gray-900 font-medium">{{ cap.call_count || 0 }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>

    <!-- Not Found -->
    <div v-else class="text-center py-20">
      <p class="text-gray-500">未找到该能力</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marketAPI, chatAPI } from '../api'
import { useAuth } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const { isLoggedIn, isCustomer } = useAuth()

const cap = ref(null)
const reviews = ref([])
const loading = ref(true)
const subscribing = ref(false)
const isSubscribed = ref(false)

function formatPrice(c) {
  if (c.pricing_model === 'free' || !c.price) return '免费'
  return `¥${c.price}`
}

function pricingLabel(model) {
  const map = { free: '免费使用', per_call: '按次计费', monthly: '包月订阅' }
  return map[model] || model || '-'
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN')
}

async function handleSubscribe() {
  if (!isLoggedIn.value) { router.push({ name: 'login', query: { redirect: route.fullPath } }); return }
  subscribing.value = true
  try {
    await marketAPI.subscribe(cap.value.cap_id)
    isSubscribed.value = true
  } catch (e) {
    alert(e.response?.data?.detail || '订阅失败')
  } finally {
    subscribing.value = false
  }
}

async function startChat() {
  try {
    const { data } = await chatAPI.createSession(cap.value.cap_id)
    router.push({ name: 'chat', params: { sessionId: data.session_id } })
  } catch (e) {
    alert(e.response?.data?.detail || '创建会话失败')
  }
}

onMounted(async () => {
  try {
    const { data } = await marketAPI.detail(route.params.capId)
    cap.value = data
    reviews.value = data.reviews || []
    isSubscribed.value = data.is_subscribed || false
  } catch {
    cap.value = null
  } finally {
    loading.value = false
  }
})
</script>
