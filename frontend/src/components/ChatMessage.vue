<template>
  <div class="py-2 px-4 rounded-2xl max-w-[80%] break-words whitespace-pre-wrap text-sm"
    :class="msg.role === 'user' ? 'ml-auto bg-primary-500 text-white rounded-br-md' : 'mr-auto bg-gray-100 text-gray-800 rounded-bl-md'">
    <div v-html="renderedContent"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  msg: { type: Object, required: true },
  streaming: { type: Boolean, default: false }
})

const renderedContent = computed(() => {
  let text = props.msg.content || ''
  // Simple markdown-like rendering
  text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  text = text.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 bg-gray-200/50 rounded text-xs font-mono">$1</code>')
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/\n/g, '<br>')
  if (props.streaming) {
    text += '<span class="streaming-cursor"></span>'
  }
  return text
})
</script>
