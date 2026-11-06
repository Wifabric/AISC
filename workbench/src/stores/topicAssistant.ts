import { defineStore } from 'pinia';
import { topicCall, type TopicCallParams } from '../lib/ipc';

/** Assistant control plane. Forms retain drafts locally; disk state is authoritative. */
export const useTopicAssistantStore = defineStore('topicAssistant', () => {
  async function call<T>(params: TopicCallParams): Promise<T> {
    if (!params.workspace || !params.operation.startsWith('assistant-')) {
      throw new Error('A workspace and assistant operation are required');
    }
    return topicCall<T>(params);
  }
  return { call };
});
