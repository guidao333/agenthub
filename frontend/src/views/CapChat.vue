<template>
  <div class="flex flex-col h-screen bg-gray-50">
    <!-- 顶部栏 -->
    <header class="flex-shrink-0 h-14 bg-gray-950 flex items-center gap-3 px-5 shadow">
      <h1 class="text-white font-bold text-base truncate min-w-0">{{ capName || '能力对话' }}</h1>
      <div class="ml-auto flex items-center gap-3">
        <span
          class="rounded-lg px-2.5 py-1 text-xs font-medium"
          :class="clientOnline ? 'bg-emerald-700 text-emerald-100' : 'bg-gray-700 text-gray-300'"
        >
          {{ clientOnline === null ? '检测中...' : clientOnline ? `客户端在线 ${onlineCount}` : '客户端离线' }}
        </span>
        <router-link :to="`/cap-config/${capId}`" class="text-slate-300 hover:text-white text-sm">配置</router-link>
        <router-link to="/dashboard" class="text-slate-300 hover:text-white text-sm">控制台</router-link>
      </div>
    </header>

    <!-- 初始化错误 -->
    <div v-if="initError" class="flex-1 flex items-center justify-center px-4">
      <div class="text-center max-w-sm">
        <h2 class="text-lg font-bold text-gray-900 mb-2">{{ initError.title }}</h2>
        <p class="text-sm text-gray-500 mb-5">{{ initError.message }}</p>
        <router-link to="/" class="text-blue-600 text-sm underline">返回能力市场</router-link>
      </div>
    </div>

    <template v-else>
      <!-- 消息列表 -->
      <main ref="chatRef" class="flex-1 overflow-y-auto">
        <div class="max-w-3xl mx-auto px-4 py-5 space-y-4">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="flex gap-3"
            :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
          >
            <div
              class="flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
              :class="msg.role === 'user' ? 'bg-emerald-600' : 'bg-blue-600'"
            >
              {{ msg.role === 'user' ? '我' : 'AI' }}
            </div>
            <div
              class="max-w-[78%] rounded-xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words"
              :class="msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-200 text-gray-800'"
            >
              <span v-if="msg.loading" class="animate-pulse">正在处理...</span>
              <span v-else>{{ msg.text }}</span>
            </div>
          </div>
        </div>
      </main>

      <!-- 快捷操作 -->
      <div v-if="quickActions.length && messages.length <= 1" class="flex-shrink-0 max-w-3xl w-full mx-auto px-4 pb-2 flex flex-wrap gap-2">
        <button
          v-for="action in quickActions"
          :key="action.label"
          type="button"
          class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          @click="quickSend(action.text)"
        >
          {{ action.label }}
        </button>
      </div>

      <!-- 输入框 -->
      <footer class="flex-shrink-0 bg-white border-t border-gray-200">
        <div class="max-w-3xl mx-auto px-4 py-3 flex gap-3 items-end">
          <textarea
            ref="inputRef"
            v-model="inputText"
            placeholder="输入消息..."
            rows="1"
            :disabled="sending || !sessionId"
            class="flex-1 min-h-[42px] max-h-32 resize-none rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 disabled:bg-gray-50 disabled:text-gray-400"
            @input="autoResize"
            @keydown.enter.exact.prevent="send"
            @keydown.enter.shift.exact="() => {}"
          ></textarea>
          <button
            type="button"
            :disabled="sending || !inputText.trim() || !sessionId"
            class="flex-shrink-0 h-[42px] rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
            @click="send"
          >
            发送
          </button>
        </div>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { capChatAPI, dashboardAPI } from '../api'

const route = useRoute()
const capId = computed(() => route.params.capId)

const capName = ref('')
const sessionId = ref('')
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const initError = ref(null)
const clientOnline = ref(null)
const onlineCount = ref(0)
const chatRef = ref(null)
const inputRef = ref(null)

let statusTimer = null

const QUICK_ACTIONS = {
  'isp-smart-cs': [
    { label: '查询账号', text: '查询账号 ABC123 的状态' },
    { label: '续费', text: '给账号 ABC123 续费 3 个月' },
    { label: '查询 ONU', text: '查询账号 ABC123 的 ONU 光猫状态' },
    { label: '派工单', text: '为账号 ABC123 派一个网络故障工单' },
  ],
  'ai-smart-monitor': [
    { label: '触发巡检', text: '触发一次 AI 巡检' },
    { label: '查询事件', text: '查询最近 24 小时的告警事件' },
    { label: '巡检评分', text: '查看最近 7 天的巡检评分' },
    { label: '摄像头状态', text: '查看所有摄像头在线状态' },
  ],
}

const WELCOME = {
  'isp-smart-cs': '你好，我是 ISP 智能客服助手。可以帮你查询账号、续费、停复机、派工单、查询或重启 ONU。',
  'ai-smart-monitor': '你好，我是 AI 智能监控助手。可以帮你触发巡检、查询告警事件、查看巡检评分和摄像头状态。',
}

const quickActions = computed(() => QUICK_ACTIONS[capId.value] || [])

let msgSeq = 0
function addMsg(role, text, loading = false) {
  const id = `m${++msgSeq}`
  messages.value.push({ id, role, text, loading })
  scrollToBottom()
  return id
}

function updateMsg(id, text) {
  const msg = messages.value.find(m => m.id === id)
  if (msg) {
    msg.text = text
    msg.loading = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight
  })
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 128) + 'px'
}

async function checkClientStatus() {
  try {
    const { data } = await dashboardAPI.clientStatus()
    const d = data?.data || data || {}
    const devices = d.devices || []
    const matched = devices.filter(dev =>
      (dev.plugin_capabilities || []).some(p => p.cap_id === capId.value)
    )
    clientOnline.value = matched.length > 0
    onlineCount.value = matched.length
  } catch {
    clientOnline.value = false
    onlineCount.value = 0
  }
}

async function send() {
  const text = inputText.value.trim()
  if (!text || sending.value || !sessionId.value) return

  inputText.value = ''
  if (inputRef.value) inputRef.value.style.height = 'auto'
  addMsg('user', text)
  const loadingId = addMsg('assistant', '', true)
  sending.value = true

  try {
    const { data } = await capChatAPI.chat(sessionId.value, text)
    updateMsg(loadingId, data.reply || '已处理。')
    checkClientStatus()
  } catch (e) {
    updateMsg(loadingId, e.response?.data?.detail || '请求失败，请重试。')
  } finally {
    sending.value = false
    nextTick(() => inputRef.value?.focus())
  }
}

function quickSend(text) {
  inputText.value = text
  send()
}

onMounted(async () => {
  try {
    const { data } = await capChatAPI.createSession(capId.value)
    sessionId.value = data.session_id
    capName.value = data.cap_name || capId.value

    const welcome = WELCOME[capId.value] || '你好，请告诉我需要处理什么。'
    addMsg('assistant', welcome)

    await checkClientStatus()
    statusTimer = setInterval(checkClientStatus, 30000)
  } catch (e) {
    const status = e.response?.status
    initError.value = status === 403
      ? { title: '尚未订阅该能力', message: '请返回市场确认订阅状态后再进入对话。' }
      : { title: '初始化失败', message: e.response?.data?.detail || e.message || '请刷新重试。' }
  }
})

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer)
})
</script>
