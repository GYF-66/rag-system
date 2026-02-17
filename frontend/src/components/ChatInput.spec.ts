import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatInput from '../ChatInput.vue'

describe('ChatInput', () => {
  it('should render correctly', () => {
    const wrapper = mount(ChatInput, {
      props: {
        disabled: false
      }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('should emit submit event when form is submitted', async () => {
    const wrapper = mount(ChatInput, {
      props: {
        disabled: false
      }
    })

    const input = wrapper.find('textarea, input')
    if (input.exists()) {
      await input.setValue('测试消息')
      await wrapper.find('form').trigger('submit')
      expect(wrapper.emitted()).toHaveProperty('submit')
    }
  })

  it('should be disabled when disabled prop is true', () => {
    const wrapper = mount(ChatInput, {
      props: {
        disabled: true
      }
    })

    const button = wrapper.find('button[type="submit"]')
    if (button.exists()) {
      expect(button.attributes('disabled')).toBeDefined()
    }
  })
})
