import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({
    sidebarOpen: true,
  }),
  actions: {
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },
    openSidebar() {
      this.sidebarOpen = true
    },
    closeSidebar() {
      this.sidebarOpen = false
    },
  },
})
