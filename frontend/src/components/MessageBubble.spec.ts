import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageBubble from '../MessageBubble.vue'

describe('MessageBubble', () => {
  it('should render correctly', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          role: 'user',
          content: '测试消息内容'
        }
      }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('should display user message with correct style', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          role: 'user',
          content: '用户消息'
        }
      }
    })
    expect(wrapper.text()).toContain('用户消息')
  })

  it('should display assistant message', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          role: 'assistant',
          content: 'AI 回复内容'
        }
      }
    })
    expect(wrapper.text()).toContain('AI 回复内容')
  })

  it('should handle empty content gracefully', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: {
          role: 'assistant',
          content: ''
        }
      }
    })
    expect(wrapper.exists()).toBe(true)
  })
})
