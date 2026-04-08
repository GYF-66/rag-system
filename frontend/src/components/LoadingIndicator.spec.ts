import { mount } from '@vue/test-utils';

import LoadingIndicator from './LoadingIndicator.vue';

describe('LoadingIndicator', () => {
  it('renders the robot avatar', () => {
    const wrapper = mount(LoadingIndicator);

    expect(wrapper.find('.fa-robot').exists()).toBe(true);
  });

  it('renders three animated dots', () => {
    const wrapper = mount(LoadingIndicator);

    expect(wrapper.findAll('span')).toHaveLength(3);
  });
});
