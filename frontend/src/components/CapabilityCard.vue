<template>
  <div class="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg hover:border-primary-200 transition-all cursor-pointer group" @click="$emit('click')">
    <div class="flex items-start justify-between mb-3">
      <div class="flex items-center gap-3">
        <div class="w-11 h-11 rounded-xl flex items-center justify-center text-lg" :class="iconBg">
          {{ cap.name.charAt(0) }}
        </div>
        <div>
          <h3 class="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">{{ cap.name }}</h3>
          <p class="text-xs text-gray-500">{{ cap.developer_name || '未知开发者' }}</p>
        </div>
      </div>
      <div v-if="cap.avg_rating" class="flex items-center gap-1 text-sm text-amber-500">
        <svg class="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
        {{ cap.avg_rating.toFixed(1) }}
      </div>
    </div>

    <p class="text-sm text-gray-600 mb-3 line-clamp-2">{{ cap.description }}</p>

    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span v-if="cap.category" class="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{{ cap.category }}</span>
        <span v-if="cap.tags && cap.tags.length" class="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded-full">{{ cap.tags[0] }}</span>
      </div>
      <div class="flex items-center gap-3 text-xs text-gray-500">
        <span class="flex items-center gap-1">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
          {{ formatNumber(cap.call_count) }}
        </span>
        <span class="font-medium" :class="cap.price > 0 ? 'text-amber-600' : 'text-green-600'">
          {{ formatPrice(cap) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  cap: { type: Object, required: true }
})

defineEmits(['click'])

const iconBg = 'bg-primary-50 text-primary-600'

function formatNumber(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

function formatPrice(cap) {
  if (cap.pricing_model === 'free' || !cap.price) return '免费'
  if (cap.pricing_model === 'per_call') return `¥${cap.price}/次`
  if (cap.pricing_model === 'monthly') return `¥${cap.price}/月`
  return `¥${cap.price}`
}
</script>
