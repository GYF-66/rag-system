import { mount } from '@vue/test-utils';

import ChatInput from './ChatInput.vue';

describe('ChatInput', () => {
  it('renders placeholder text', () => {
    const wrapper = mount(ChatInput, {
      props: { placeholder: '请输入问题' },
    });

    expect(wrapper.get('textarea').attributes('placeholder')).toBe('请输入问题');
  });

  it('emits send with trimmed content when button is clicked', async () => {
    const wrapper = mount(ChatInput);

    await wrapper.get('textarea').setValue('  测试消息  ');
    await wrapper.get('button').trigger('click');

    expect(wrapper.emitted('send')).toEqual([['测试消息']]);
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('');
  });

  it('emits send on Enter but keeps newline behavior for Shift+Enter', async () => {
    const wrapper = mount(ChatInput);
    const textarea = wrapper.get('textarea');

    await textarea.setValue('回车发送');
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: false, preventDefault: vi.fn() });

    expect(wrapper.emitted('send')).toEqual([['回车发送']]);

    await textarea.setValue('换行');
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: true, preventDefault: vi.fn() });

    expect(wrapper.emitted('send')).toHaveLength(1);
  });

  it('disables sending when loading or disabled', () => {
    const loadingWrapper = mount(ChatInput, { props: { loading: true } });
    const disabledWrapper = mount(ChatInput, { props: { disabled: true } });

    expect(loadingWrapper.get('button').attributes('disabled')).toBeDefined();
    expect(disabledWrapper.get('textarea').attributes('disabled')).toBeDefined();
  });
});
