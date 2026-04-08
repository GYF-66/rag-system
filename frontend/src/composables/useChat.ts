import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import { apiClient } from '@/services/api';
import type { ChatMessage } from '@/types';

export const chatKeys = {
  all: ['chat'] as const,
  conversations: () => [...chatKeys.all, 'conversations'] as const,
  conversation: (id: string) => [...chatKeys.all, 'conversation', id] as const,
  messages: (conversationId: string) => [...chatKeys.all, 'messages', conversationId] as const,
};

export function useSendChatMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: { message: string; conversationId?: string }) => {
      if (params.conversationId) {
        apiClient.setSession(params.conversationId);
      }
      return apiClient.chat(params.message);
    },
    onMutate: async (variables) => {
      const conversationId = variables.conversationId || 'draft';
      const queryKey = chatKeys.messages(conversationId);
      await queryClient.cancelQueries({ queryKey });
      const previousMessages = queryClient.getQueryData<ChatMessage[]>(queryKey);

      const optimisticMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: variables.message,
        createdAt: new Date().toISOString(),
      };

      queryClient.setQueryData<ChatMessage[]>(queryKey, (old = []) => [...old, optimisticMessage]);
      return { previousMessages, conversationId };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousMessages) {
        queryClient.setQueryData(chatKeys.messages(context.conversationId), context.previousMessages);
      }
    },
    onSuccess: (data, _variables, context) => {
      const conversationId = data.session_id || context?.conversationId || 'draft';
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(conversationId) });
      queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
  });
}

export function useConversationsQuery() {
  return useQuery({
    queryKey: chatKeys.conversations(),
    queryFn: async () => [],
    staleTime: 5 * 60 * 1000,
  });
}

export function useConversationMessagesQuery(conversationId: string) {
  return useQuery({
    queryKey: chatKeys.messages(conversationId),
    queryFn: async () => [] as ChatMessage[],
    enabled: !!conversationId,
    staleTime: 2 * 60 * 1000,
  });
}

export function useClearConversationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (conversationId: string) => ({ success: true, conversationId }),
    onSuccess: (_data, conversationId) => {
      queryClient.setQueryData(chatKeys.messages(conversationId), []);
      queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
  });
}

export function useDeleteConversationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (conversationId: string) => ({ success: true, conversationId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
  });
}
