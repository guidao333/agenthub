<template>
  <button
    type="button"
    class="group flex h-full w-full flex-col rounded-lg border border-gray-200 bg-white p-5 text-left transition hover:-translate-y-0.5 hover:border-primary-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-200"
    @click="$emit('click')"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="flex min-w-0 items-start gap-3">
        <div
          class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-base font-bold"
          :class="accent.icon"
        >
          {{ iconText }}
        </div>
        <div class="min-w-0">
          <h3 class="truncate text-base font-semibold text-gray-950 transition-colors group-hover:text-primary-700">
            {{ cap.name }}
          </h3>
          <p class="mt-0.5 truncate text-xs text-gray-500">
            {{ cap.developer_name || 'AgentHub 官方' }}
          </p>
        </div>
      </div>
      <span class="shrink-0 text-sm font-semibold" :class="accent.price">
        {{ formatPrice(cap) }}
      </span>
    </div>

    <p class="mt-4 min-h-[48px] text-sm leading-6 text-gray-600">
      {{ shortDescription }}
    </p>

    <div class="mt-4 flex min-h-[28px] flex-wrap gap-2">
      <span
        v-for="tag in visibleTags"
        :key="tag"
        class="rounded-md bg-gray-100 px-2 py-1 text-xs text-gray-600"
      >
        {{ tag }}
      </span>
    </div>

    <div class="mt-auto pt-5">
      <div class="flex items-center justify-between border-t border-gray-100 pt-4 text-xs text-gray-500">
        <span>{{ formatNumber(cap.call_count) }} 次调用</span>
        <span v-if="cap.avg_rating" class="font-medium text-amber-600">
          {{ Number(cap.avg_rating).toFixed(1) }} 分
        </span>
        <span v-else class="text-gray-400">待评分</span>
      </div>
    </div>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  cap: { type: Object, required: true },
})

defineEmits(['click'])

const accent = computed(() => {
  if (props.cap.cap_id === 'ai-smart-monitor') {
    return { icon: 'bg-violet-50 text-violet-700', price: 'text-violet-700' }
  }
  if (props.cap.cap_id === 'isp-smart-cs') {
    return { icon: 'bg-blue-50 text-blue-700', price: 'text-blue-700' }
  }
  return { icon: 'bg-emerald-50 text-emerald-700', price: 'text-emerald-700' }
})

const iconText = computed(() => {
  const name = props.cap.name || 'AI'
  return name.includes('AI') ? 'AI' : name.charAt(0)
})

const shortDescription = computed(() => {
  const text = props.cap.description || '可订阅、可配置、可通过对话使用的行业AI能力。'
  return text.length > 86 ? `${text.slice(0, 86)}...` : text
})

const visibleTags = computed(() => (props.cap.tags || []).slice(0, 4))

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
</script>
