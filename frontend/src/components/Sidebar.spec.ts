import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Sidebar from '../Sidebar.vue'
import { createPinia, setActivePinia } from 'pinia'

describe('Sidebar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should render correctly', () => {
    const wrapper = mount(Sidebar, {
      global: {
        stubs: ['router-link']
      }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('should have new chat button', () => {
    const wrapper = mount(Sidebar, {
      global: {
        stubs: ['router-link']
      }
    })
    const button = wrapper.find('button')
    expect(button.exists()).toBe(true)
  })
})
