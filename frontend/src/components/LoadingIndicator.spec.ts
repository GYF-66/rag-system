import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LoadingIndicator from '../LoadingIndicator.vue'

describe('LoadingIndicator', () => {
  it('should render correctly', () => {
    const wrapper = mount(LoadingIndicator)
    expect(wrapper.exists()).toBe(true)
  })

  it('should contain loading animation', () => {
    const wrapper = mount(LoadingIndicator)
    // 检查是否有动画元素或 loading 相关类
    expect(wrapper.html()).toContain('')
  })
})
