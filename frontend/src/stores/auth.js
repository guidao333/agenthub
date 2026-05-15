import { ref, computed } from 'vue'

const token = ref(localStorage.getItem('token') || '')
const role = ref(localStorage.getItem('role') || '')
const username = ref(localStorage.getItem('username') || '')

const isLoggedIn = computed(() => !!token.value)
const isCustomer = computed(() => role.value === 'customer')
const isDeveloper = computed(() => role.value === 'developer')
const isAdmin = computed(() => role.value === 'admin')

function setAuth(data) {
  token.value = data.access_token
  role.value = data.role
  username.value = data.username
  localStorage.setItem('token', data.access_token)
  localStorage.setItem('role', data.role)
  localStorage.setItem('username', data.username)
}

function clearAuth() {
  token.value = ''
  role.value = ''
  username.value = ''
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.removeItem('username')
}

export function useAuth() {
  return {
    token, role, username,
    isLoggedIn, isCustomer, isDeveloper, isAdmin,
    setAuth, clearAuth,
  }
}
