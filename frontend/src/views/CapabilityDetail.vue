<template>
  <div class="bg-white min-h-screen">
    <div v-if="loading" class="flex justify-center py-24">
      <div class="w-8 h-8 border-4 border-primary-100 border-t-primary-600 rounded-full animate-spin"></div>
    </div>

    <div v-else-if="cap">
      <section class="border-b border-gray-200 bg-white">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          <button @click="$router.back()" class="text-sm text-gray-500 hover:text-gray-800 mb-8">
            返回能力市场
          </button>

          <p class="text-sm font-semibold mb-3" :class="detail.accentText">{{ detail.kicker }}</p>
          <h1 class="text-4xl lg:text-6xl font-bold text-gray-950 tracking-tight leading-tight">{{ cap.name }}</h1>
          <p class="mt-6 text-xl text-gray-600 leading-9 max-w-4xl">{{ detail.hero }}</p>

          <div class="mt-8 flex flex-wrap gap-2">
            <span v-for="tag in cap.tags || []" :key="tag" class="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-sm">
              {{ tag }}
            </span>
          </div>

          <div class="mt-8 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div class="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <span>
                  <b class="text-gray-950">{{ formatPrice(cap) }}</b>
                  <span v-if="detail.annualPrice" class="text-gray-950 font-semibold"> · {{ detail.annualPrice }}/</span>
                  <span class="text-gray-500 ml-1">{{ pricingLabel(cap.pricing_model) }}</span>
                </span>
                <span class="text-gray-600">评分 {{ cap.avg_rating || '-' }}</span>
                <span class="text-gray-600">调用 {{ formatNumber(cap.call_count) }}</span>
                <span v-if="isSubscribed" class="text-emerald-700 font-medium">已订阅</span>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-if="!isSubscribed"
                  :disabled="subscribing"
                  class="h-10 px-5 rounded-lg bg-primary-600 text-white text-sm font-semibold hover:bg-primary-700 disabled:opacity-60"
                  @click="handleSubscribe"
                >
                  {{ subscribing ? '订阅..' : '立即订阅' }}
                </button>
                <template v-else>
                  <router-link :to="`/cap-config/${cap.cap_id}`" class="h-10 px-4 inline-flex items-center rounded-lg bg-gray-950 text-white text-sm font-semibold hover:bg-gray-800">
                    配置能力
                  </router-link>
                  <router-link :to="`/cap-chat/${cap.cap_id}`" class="h-10 px-4 inline-flex items-center rounded-lg border border-gray-300 text-gray-800 text-sm font-semibold hover:bg-white">
                    打开能力对话
                  </router-link>
                  <a href="/downloads/AgentHubClientSetup-1.0.17.exe" class="h-10 px-4 inline-flex items-center rounded-lg border border-gray-300 text-gray-800 text-sm font-semibold hover:bg-white">
                    下载 Windows 安装                  </a>
                </template>
              </div>
            </div>
          </div>
        </div>
      </section>

      <main class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <section class="py-12 lg:py-16 border-b border-gray-200">
          <p class="text-sm font-semibold text-gray-500 mb-3">01 / 能力说明</p>
          <h2 class="text-3xl font-bold text-gray-950">这个能力解决什么问</h2>
          <p class="mt-6 text-lg text-gray-700 leading-9 max-w-4xl whitespace-pre-line">{{ detail.description }}</p>
        </section>

        <section class="py-12 lg:py-16 border-b border-gray-200">
          <p class="text-sm font-semibold text-gray-500 mb-3">02 / 核心能力</p>
          <h2 class="text-3xl font-bold text-gray-950">模块能力清单</h2>
          <div class="mt-8 divide-y divide-gray-200">
            <div v-for="(item, index) in detail.features" :key="item.title" class="grid md:grid-cols-[120px_1fr] gap-4 py-6">
              <div class="text-sm font-semibold" :class="detail.accentText">{{ String(index + 1).padStart(2, '0') }}</div>
              <div>
                <h3 class="text-xl font-bold text-gray-950">{{ item.title }}</h3>
                <p class="mt-3 text-gray-600 leading-7">{{ item.text }}</p>
              </div>
            </div>
          </div>
        </section>

        <section v-if="detail.workflow.length" class="py-12 lg:py-16 border-b border-gray-200">
          <p class="text-sm font-semibold text-gray-500 mb-3">03 / 部署流程</p>
          <h2 class="text-3xl font-bold text-gray-950">从接入到使用</h2>
          <div class="mt-8 space-y-5">
            <div v-for="(step, index) in detail.workflow" :key="step" class="flex gap-4">
              <div class="w-9 h-9 rounded-full bg-gray-950 text-white flex items-center justify-center text-sm font-semibold shrink-0">
                {{ index + 1 }}
              </div>
              <p class="pt-1.5 text-gray-700 leading-7">{{ step }}</p>
            </div>
          </div>
        </section>

        <section v-if="detail.pricing?.length" class="py-12 lg:py-16 border-b border-gray-200">
          <p class="text-sm font-semibold text-gray-500 mb-3">04 / 价格参</p>
          <h2 class="text-3xl font-bold text-gray-950">细分能力与订阅方</h2>
          <div class="mt-8 overflow-x-auto">
            <table class="min-w-full text-sm">
              <thead>
                <tr class="text-left text-gray-500 border-b border-gray-200">
                  <th class="py-3 pr-4">能力</th>
                  <th class="py-3 pr-4">月付</th>
                  <th class="py-3 pr-4">年付</th>
                  <th class="py-3">说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in detail.pricing" :key="row.name" class="border-b border-gray-100 last:border-0">
                  <td class="py-4 pr-4 font-medium text-gray-950">{{ row.name }}</td>
                  <td class="py-4 pr-4">{{ row.monthly }}</td>
                  <td class="py-4 pr-4">{{ row.yearly }}</td>
                  <td class="py-4 text-gray-600">{{ row.note }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="py-12 lg:py-16 border-b border-gray-200">
          <p class="text-sm font-semibold text-gray-500 mb-3">{{ detail.pricing?.length ? '05' : '04' }} / 适用场景</p>
          <h2 class="text-3xl font-bold text-gray-950">可以落地的现</h2>
          <div class="mt-8 flex flex-wrap gap-2">
            <span v-for="scene in detail.scenes" :key="scene" class="px-3 py-2 rounded-full bg-gray-100 text-gray-700 text-sm">
              {{ scene }}
            </span>
          </div>
        </section>

        <section class="py-12 lg:py-16">
          <div class="grid lg:grid-cols-2 gap-10">
            <div>
              <p class="text-sm font-semibold text-gray-500 mb-3">{{ detail.pricing?.length ? '06' : '05' }} / 价</p>
              <h2 class="text-3xl font-bold text-gray-950">为什么选择</h2>
              <ul class="mt-6 space-y-4 text-gray-700">
                <li v-for="value in detail.values" :key="value" class="leading-7">{{ value }}</li>
              </ul>
            </div>
            <div>
              <p class="text-sm font-semibold text-gray-500 mb-3">{{ detail.pricing?.length ? '07' : '06' }} / 技术接</p>
              <h2 class="text-3xl font-bold text-gray-950">系统对接方式</h2>
              <dl class="mt-6 divide-y divide-gray-200 text-sm">
                <div v-for="item in detail.tech" :key="item.label" class="flex justify-between gap-4 py-4">
                  <dt class="text-gray-500">{{ item.label }}</dt>
                  <dd class="font-medium text-gray-900 text-right">{{ item.value }}</dd>
                </div>
              </dl>
            </div>
          </div>
        </section>
      </main>
    </div>

    <div v-else class="text-center py-24">
      <p class="text-gray-500">未找到该能力</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marketAPI } from '../api'
import { useAuth } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = useAuth()

const cap = ref(null)
const loading = ref(true)
const subscribing = ref(false)
const isSubscribed = ref(false)

const details = {
  'ai-smart-monitor': {
    kicker: 'AI 智能安防平台',
    accentText: 'text-violet-700',
    hero: '原有摄像头不换，加一个 AI 大脑，普通监控升级为 AI 智能监控。',
    description: 'AgentHub AI 智能监控面向物业小区、工业园区、商业广场。客户只需在监控室电脑安装边缘端软件，原有摄像头通过 RTSP/ONVIF 接入，历史视频默认从客户 NVR 录像主机读取。平台负责配置、事件、通知和 AI 对话，不同事件可按负责人和通知通道分别路由。',
    annualPrice: '¥9900',
    features: [
      { title: 'AI 环境卫生巡检', text: '自动识别公共区域垃圾、杂物、废弃物，输出卫生评分、抓拍图片、位置标注和扣分明细。' },
      { title: 'AI 高空抛物检测', text: '24 小时检测高空抛物，结合连续帧分析、轨迹追踪和三层过滤，发现后立即报警。' },
      { title: 'AI 智能录像回查', text: '用自然语言查询历史录像或事件，按摄像头、时间段和场景检索 NVR 片段，生成事件时间线、视频片段和分析结论。' },
      { title: 'AI 找人', text: 'AI 找人是录像回查之上的专项能力，可根据照片或文字描述检索目标出现时间、地点和行动轨迹。' },
      { title: '多通道通知', text: '飞书、企业微信、微信、短信、邮件按事件类型分发，例如卫生问题通知清洁主管，高空抛物通知保安队长。' },
      { title: '自然语言管家', text: '通过网页或飞书对话触发巡检、查报警、看评分、查设备状态，无需学习复杂系统。' },
    ],
    workflow: ['下载安装 Windows 客户端', '在本地工作台绑定 API Key', '配置摄像头接入和 NVR 品牌', '选择实时告警、录像回查、AI 找人等能力类型', '接入微信、飞书、邮件、短信通知通道', '按事件配置负责人和通知规则', '通过后台或对话使用 AI 能力'],
    pricing: [],
    scenes: ['物业小区', '工业园区', '商业广场', '地下车库', '楼道', '垃圾房周边', '学校操场', '消防通道'],
    values: ['不更换摄像头，旧设备直接利旧。', '视频推理在本地，画面不上传云端。', '不同事件自动发给对应负责人，减少人工转发。', '告警、报告和追溯形成管理闭环。'],
    tech: [
      { label: '摄像头协议', value: 'RTSP / ONVIF' },
      { label: '录像主机', value: 'NVR 品牌适配' },
      { label: '推理位置', value: '客户边缘端' },
      { label: '智能分析能力', value: '平台托管视觉分析引擎' },
      { label: '通知通道', value: '飞书 / 微信 / 短信 / 邮件' },
    ],
  },
  'isp-smart-cs': {
    kicker: 'ISP 宽带智能客服',
    accentText: 'text-blue-700',
    hero: '把计费、OLT、TR069、IPTV 和工单系统连接到统一智能客服。',
    description: 'ISP 智能客服面向宽带运运商，平台负责理解客户意图并生成结构化指令，客户本地统一客户端连接内网业务系统执行查询、故障诊断、在线状态、光猫状态、续费、停复机、派工单、ONU 管理等动作。通知通道默认覆盖全部业务能力。',
    annualPrice: '¥4990',
    features: [
      { title: '账号查询', text: '查询宽带账号状态、套餐、余额、到期时间和使用情况。' },
      { title: '续费和停复机', text: '通过对话触发续费、停机、复机等高频业务动作。' },
      { title: '故障和在线诊断', text: '查询用户是否在线、宽带故障原因、光猫在线状态、光功率、版本等关键信息。' },
      { title: '远程重启 ONU', text: '通过 TR069/OLT 管理系统远程执行重启动作。' },
      { title: '派发工单', text: '自动整理故障类型、客户账号、联系方式和故障描述，推送到工单系统。' },
      { title: '多通道业务通知', text: '微信、飞书、邮件、短信默认覆盖账号查询、故障诊断、在线状态、ONU 状态、续费结果和工单等业务能力。' },
      { title: '多系统适配', text: '支持凌风 LFRADIUS、秒开 OLT/TR069、智慧光网 IPTV，并可继续接入新系统。' },
    ],
    workflow: ['客户订阅能力', '下载安装 Windows 客户端', '在本地工作台绑定 API Key', '填写计费、TR069、OLT、IPTV 等配置', '配置统一业务通知通道', '在平台对话框处理宽带业务'],
    pricing: [],
    scenes: ['宽带营业厅', '装维客服', '网络运维值班', '物业宽带服务', '企业内网客服'],
    values: ['客服无需登录多个后台，统一通过对话处理。', '客户内网系统由统一客户端访问，降低公网暴露风险。', '查询、诊断、工单和续费结果都可通过统一通道通知。', '后续可按客户系统继续增加适配器。'],
    tech: [
      { label: '执行层', value: 'AgentHub 统一客户端' },
      { label: '通信', value: 'HTTPS WebSocket' },
      { label: '推理', value: '平台托管推理引擎' },
      { label: '通知通道', value: '飞书 / 微信 / 短信 / 邮件' },
    ],
  },
}

const detail = computed(() => details[cap.value?.cap_id] || {
  kicker: 'AgentHub 能力',
  accentText: 'text-primary-700',
  hero: cap.value?.description || '',
  description: cap.value?.long_description || cap.value?.description || '',
  annualPrice: '',
  features: [],
  workflow: [],
  pricing: [],
  scenes: cap.value?.tags || [],
  values: [],
  tech: [],
})

function formatNumber(n) {
  if (!n) return '0'
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function formatPrice(c) {
  if (c.pricing_model === 'free' || !c.price) return '免费'
  if (c.pricing_model === 'per_call') return `¥${c.price}/次`
  return `¥${c.price}/月`
}

function pricingLabel(model) {
  const map = { free: '免费使用', per_call: '按次计费', monthly: '包月订阅', subscription: '包月订阅' }
  return map[model] || model || '-'
}

async function handleSubscribe() {
  if (!isLoggedIn.value) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
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

onMounted(async () => {
  try {
    const { data } = await marketAPI.detail(route.params.capId)
    cap.value = data
    isSubscribed.value = data.is_subscribed || false
  } catch {
    cap.value = null
  } finally {
    loading.value = false
  }
})
</script>
