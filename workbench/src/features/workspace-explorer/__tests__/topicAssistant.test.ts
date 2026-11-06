import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { createPinia } from 'pinia';
import TopicAssistant from '../TopicAssistant.vue';
import { topicCall } from '../../../lib/ipc';

vi.mock('../../../lib/ipc', () => ({topicCall: vi.fn()}));
const empty = () => ({revision: 1, enabled: true, mode: 'collaborate', memories: [], baselines: []});
const result = () => ({assistant: empty(), profile: {...empty(), revision: 0, enabled: false}});
function render() {
  return mount(TopicAssistant, {props: {workspace: 'D:/test', topicId: 'topic-a'},
    global: {plugins: [createPinia(), createI18n({legacy: false, locale: 'zh-CN', messages: {}})]}});
}
beforeEach(() => {
  vi.mocked(topicCall).mockReset();
  vi.mocked(topicCall).mockImplementation(async p => (p.operation === 'assistant-skills'
    ? {skills: [{id:'story', name:'Story', source:'installed:story'}], warnings: []} : result()) as never);
});
describe('topic assistant', () => {
  it('saves mode through the revision checked API', async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('[data-testid=assistant-mode]').setValue('coach');
    await wrapper.get('[data-testid=assistant-save]').trigger('click'); await flushPromises();
    expect(topicCall).toHaveBeenCalledWith(expect.objectContaining({operation:'assistant-save',
      payload: expect.objectContaining({expected_revision:1, mode:'coach'})}));
    wrapper.unmount();
  });
  it('preserves unsaved input after a concurrent update conflict', async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('[data-testid=assistant-mode]').setValue('coach');
    vi.mocked(topicCall).mockRejectedValueOnce(new Error('changed; refresh'));
    await wrapper.get('[data-testid=assistant-save]').trigger('click'); await flushPromises();
    expect(wrapper.get('[role=alert]').text()).toContain('changed');
    expect((wrapper.get('[data-testid=assistant-mode]').element as HTMLSelectElement).value).toBe('coach');
    wrapper.unmount();
  });
  it('does not apply a response from a previously selected topic', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(topicCall).mockImplementationOnce(() => new Promise(r => {resolve = r;}) as never);
    const wrapper = render();
    await wrapper.setProps({topicId:'topic-b'}); await flushPromises();
    resolve({assistant:{...empty(),mode:'deliver'},profile:empty()}); await flushPromises();
    expect((wrapper.get('[data-testid=assistant-mode]').element as HTMLSelectElement).value).toBe('collaborate');
    wrapper.unmount();
  });
  it('pins the selected installed skill with its explicit purpose', async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('[data-testid=assistant-baseline]').setValue('story');
    await wrapper.get('input[placeholder^="例如：组织"]').setValue('Story structure');
    const button = wrapper.findAll('button').find(b => b.text() === '固定为主题基线')!;
    await button.trigger('click'); await flushPromises();
    expect(topicCall).toHaveBeenCalledWith(expect.objectContaining({operation:'assistant-pin',
      payload:{expected_revision:1,skill_id:'story',purpose:'Story structure'}}));
    wrapper.unmount();
  });
});
