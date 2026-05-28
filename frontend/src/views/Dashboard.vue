<template>
  <div class="min-h-screen bg-gray-50">
    <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p class="text-sm font-semibold text-primary-700">AgentHub 控制�?/p>
          <h1 class="mt-1 text-2xl font-bold text-gray-950">我的能力</h1>
        </div>
        <router-link
          to="/"
          class="inline-flex h-10 items-center justify-center rounded-lg border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-700 hover:bg-gray-100"
        >
          进入能力市场
        </router-link>
      </div>

      <div class="mb-6 flex w-fit gap-1 rounded-xl bg-gray-200 p-1">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="rounded-lg px-4 py-2 text-sm font-semibold transition"
          :class="activeTab === tab.key ? 'bg-white text-gray-950 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <section v-if="activeTab === 'subs'">
        <div class="mb-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p class="text-sm font-semibold text-gray-900">统一客户�?/p>
              <p class="mt-1 text-sm text-gray-500">
                {{ clientStatus.online ? `已连�?${clientStatus.online_count} 台客户端` : '未检测到在线客户�? }}
              </p>
            </div>
            <span
              class="inline-flex h-7 items-center rounded-full px-3 text-xs font-semibold"
              :class="clientStatus.online ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'"
            >
              {{ clientStatus.online ? '在线' : '离线' }}
            </span>
          </div>
          <div v-if="clientStatus.devices?.length" class="mt-4 grid gap-3 md:grid-cols-2">
            <div v-for="device in clientStatus.devices" :key="device.device_id" class="rounded-lg bg-gray-50 p-4">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="break-all font-mono text-sm font-semibold text-gray-900">{{ device.device_id }}</p>
                  <p class="mt-1 text-xs text-gray-500">
                    版本 {{ device.client_version || '-' }} · 心跳 {{ heartbeatText(device) }}
                  </p>
                </div>
                <span class="shrink-0 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">online</span>
              </div>
              <div class="mt-3 flex flex-wrap gap-2">
                <span
                  v-for="plugin in device.plugin_capabilities || []"
                  :key="plugin.cap_id"
                  class="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-700 ring-1 ring-gray-200"
                >
                  {{ plugin.name || plugin.cap_id }} · {{ (plugin.actions || []).length }} 个动�?                </span>
              </div>
            </div>
          </div>
          <p v-else class="mt-4 text-sm text-gray-500">
            下载 Windows 免安装版统一客户端，双击运行后在本地工作台绑�?API Key，这里会显示设备 ID、版本、插件和心跳�?          </p>
        </div>

        <div v-if="loading" class="rounded-lg border border-gray-200 bg-white p-10 text-center text-gray-500">
          正在加载订阅能力...
        </div>

        <div v-else-if="subs.length" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <article
            v-for="sub in subs"
            :key="sub.id"
            class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
          >
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div class="flex items-center gap-3">
                  <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-gray-950 text-base font-bold text-white">
                    {{ capabilityInitial(sub) }}
                  </div>
                  <div>
                    <h2 class="text-lg font-bold text-gray-950">{{ sub.capability_name || sub.name }}</h2>
                    <p class="mt-0.5 text-xs text-gray-500">
                      {{ sub.cap_id }} · 订阅�?{{ formatDate(sub.started_at || sub.created_at) }}
                    </p>
                  </div>
                </div>
              </div>
              <span
                class="inline-flex h-7 items-center rounded-full px-3 text-xs font-semibold"
                :class="sub.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'"
              >
                {{ sub.status === 'active' ? '有效订阅' : sub.status }}
              </span>
            </div>

            <div class="mt-5 rounded-lg bg-gray-50 p-4">
              <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div class="min-w-0">
                  <p class="text-xs font-semibold text-gray-500">客户�?API Key</p>
                  <p class="mt-1 break-all font-mono text-sm text-gray-800">{{ maskKey(sub.api_key) }}</p>
                </div>
                <button
                  type="button"
                  class="h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm font-semibold text-gray-700 hover:bg-gray-100"
                  @click="copyKey(sub.api_key)"
                >
                  复制 Key
                </button>
              </div>
            </div>

            <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <router-link
                :to="`/cap-config/${sub.cap_id}`"
                class="inline-flex h-10 items-center justify-center rounded-lg bg-gray-950 px-4 text-sm font-semibold text-white hover:bg-gray-800"
              >
                配置能力
              </router-link>
              <router-link
                :to="`/cap-chat/${sub.cap_id}`"
                class="inline-flex h-10 items-center justify-center rounded-lg border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-800 hover:bg-gray-100"
              >
                打开能力对话
              </router-link>
              <a
                href="/downloads/AgentHubClientSetup-1.0.17.exe"
                class="inline-flex h-10 items-center justify-center rounded-lg border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-800 hover:bg-gray-100"
              >
                下载 Windows 安装�?              </a>
              <button
                type="button"
                class="inline-flex h-10 items-center justify-center rounded-lg border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-800 hover:bg-gray-100"
                @click="goVueChat(sub)"
              >
                平台对话
              </button>
            </div>

            <div class="mt-5 border-t border-gray-100 pt-4">
              <p class="text-sm font-semibold text-gray-900">上线使用顺序</p>
              <ol class="mt-3 space-y-2 text-sm text-gray-600">
                <li v-for="step in usageSteps(sub)" :key="step" class="flex gap-2 leading-6">
                  <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400"></span>
                  <span>{{ step }}</span>
                </li>
              </ol>
            </div>
          </article>
        </div>

        <div v-else class="rounded-lg border border-gray-200 bg-white px-6 py-16 text-center">
          <h2 class="text-lg font-bold text-gray-950">暂无订阅的能�?/h2>
          <p class="mt-2 text-sm text-gray-500">订阅 ISP 智能客服�?AI 智能监控后，这里会显示配置、客户端和对话入口�?/p>
          <router-link to="/" class="mt-5 inline-flex h-10 items-center rounded-lg bg-primary-600 px-4 text-sm font-semibold text-white hover:bg-primary-700">
            去市场订�?          </router-link>
        </div>
      </section>

      <section v-if="activeTab === 'usage'" class="rounded-lg border border-gray-200 bg-white p-6">
        <h2 class="text-lg font-bold text-gray-950">使用统计</h2>
        <div v-if="usage.length" class="mt-4 divide-y divide-gray-100">
          <div v-for="item in usage" :key="item.capability_id || item.cap_id || item.name" class="flex items-center justify-between py-3 text-sm">
            <div>
              <p class="font-semibold text-gray-900">{{ item.capability_name || item.name }}</p>
              <p class="mt-0.5 text-xs text-gray-500">{{ item.cap_id || item.capability_id }}</p>
            </div>
            <div class="text-right">
              <p class="font-semibold text-gray-950">{{ item.call_count || item.calls || 0 }} �?/p>
              <p class="mt-0.5 text-xs text-gray-500">花费 ¥{{ Number(item.cost ?? item.charged ?? 0).toFixed(2) }}</p>
            </div>
          </div>
        </div>
        <p v-else class="mt-4 text-sm text-gray-500">暂无使用记录�?/p>
      </section>

      <section v-if="activeTab === 'keys'" class="rounded-lg border border-gray-200 bg-white p-6">
        <h2 class="text-lg font-bold text-gray-950">API Key</h2>
        <div v-if="apiKeys.length" class="mt-4 space-y-3">
          <div v-for="key in apiKeys" :key="key.subscription_id" class="flex flex-col gap-3 rounded-lg bg-gray-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="font-mono text-sm text-gray-800">{{ maskKey(key.api_key) }}</p>
              <p class="mt-1 text-xs text-gray-500">{{ key.capability_name }}</p>
            </div>
            <button type="button" class="h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm font-semibold text-gray-700" @click="copyKey(key.api_key)">
              复制
            </button>
          </div>
        </div>
        <p v-else class="mt-4 text-sm text-gray-500">订阅能力后会自动生成 API Key�?/p>
      </section>

      <section v-if="activeTab === 'bills'" class="rounded-lg border border-gray-200 bg-white p-6">
        <h2 class="text-lg font-bold text-gray-950">账单记录</h2>
        <p v-if="!bills.length" class="mt-4 text-sm text-gray-500">暂无账单�?/p>
        <div v-else class="mt-4 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200 text-left text-gray-500">
                <th class="py-2 pr-4 font-semibold">时间</th>
                <th class="py-2 pr-4 font-semibold">描述</th>
                <th class="py-2 text-right font-semibold">金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="bill in bills" :key="bill.id" class="border-b border-gray-100 last:border-0">
                <td class="py-3 pr-4 text-gray-600">{{ formatDate(bill.created_at) }}</td>
                <td class="py-3 pr-4 text-gray-800">{{ bill.description || bill.type }}</td>
                <td class="py-3 text-right font-semibold" :class="bill.amount > 0 ? 'text-emerald-600' : 'text-red-600'">
                  {{ bill.amount > 0 ? '+' : '' }}¥{{ Math.abs(bill.amount || 0).toFixed(2) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { chatAPI, dashboardAPI } from '../api'

const router = useRouter()
const activeTab = ref('subs')
const loading = ref(true)
const subs = ref([])
const usage = ref([])
const bills = ref([])
const apiKeys = ref([])
const clientStatus = ref({ online: false, online_count: 0, devices: [] })

const tabs = [
  { key: 'subs', label: '我的订阅' },
  { key: 'usage', label: '使用统计' },
  { key: 'keys', label: 'API Key' },
  { key: 'bills', label: '账单' },
]

function unwrap(data, fallback = []) {
  if (data?.success && data.data !== undefined) return data.data
  return data?.items || data || fallback
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('zh-CN')
}

function maskKey(key) {
  if (!key) return '未生�?
  if (key.length <= 14) return key
  return `${key.slice(0, 8)}...${key.slice(-6)}`
}

function capabilityInitial(sub) {
  return (sub.capability_name || sub.name || '?').slice(0, 1)
}

function copyKey(key) {
  if (!key) return
  navigator.clipboard.writeText(key).then(() => {
    window.alert('API Key 已复�?)
  })
}

function heartbeatText(device) {
  const age = device?.last_heartbeat_age_seconds
  if (age == null) return '暂无心跳'
  if (age < 60) return `${age} 秒前`
  return `${Math.floor(age / 60)} 分钟前`
}

function usageSteps(sub) {
  if (sub.cap_id === 'ai-smart-monitor') {
    return [
      '下载安装 Windows 客户端并在客户现场监控室电脑或边缘盒子上运行�?,
      '打开 Windows 客户端，在本地工作台绑定 API Key�?,
      '在配置页填写摄像头接入、NVR 品牌、AI 能力类型和通知通道�?,
      '先测试通知，再打开能力对话或事件面板进行巡检、告警和录像回查�?,
    ]
  }
  if (sub.cap_id === 'isp-smart-cs') {
    return [
      '下载安装 Windows 客户端并部署在能访问计费、OLT、TR069、IPTV 系统的内网电脑上�?,
      '打开 Windows 客户端，在本地工作台绑定 API Key，并保持客户端在线�?,
      '在配置页选择计费系统、OLT 管理系统、TR069 光猫管理系统�?IPTV 系统�?,
      '配置业务通知通道后，打开能力对话处理查询、故障诊断、续费和工单�?,
    ]
  }
  return [
    '下载安装 Windows 客户端或按能力说明完成接入�?,
    '在本地工作台绑定 API Key�?,
    '完成能力配置�?,
    '打开能力对话开始使用�?,
  ]
}

async function goVueChat(sub) {
  try {
    const { data } = await chatAPI.createSession(sub.capability_id)
    router.push({ name: 'chat', params: { sessionId: data.session_id } })
  } catch (error) {
    window.alert(error.response?.data?.detail || '创建会话失败')
  }
}

async function loadDashboard() {
  loading.value = true
  try {
    const { data } = await dashboardAPI.subscriptions()
    const list = unwrap(data)
    subs.value = Array.isArray(list) ? list.filter(item => item.status === 'active') : []
  } finally {
    loading.value = false
  }

  try {
    const { data } = await dashboardAPI.usage()
    const value = unwrap(data, {})
    usage.value = Array.isArray(value) ? value : (value.by_capability || [])
  } catch {}

  try {
    const { data } = await dashboardAPI.bills()
    const list = unwrap(data)
    bills.value = Array.isArray(list) ? list : []
  } catch {}

  try {
    const { data } = await dashboardAPI.apiKeys()
    const list = unwrap(data)
    apiKeys.value = Array.isArray(list) ? list : []
  } catch {}

  try {
    const { data } = await dashboardAPI.clientStatus()
    clientStatus.value = unwrap(data, { online: false, online_count: 0, devices: [] })
  } catch {
    clientStatus.value = { online: false, online_count: 0, devices: [] }
  }
}

onMounted(loadDashboard)
</script>
