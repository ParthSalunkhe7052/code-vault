import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { webhooks } from '../services/api';
import { Webhook, CreateWebhookRequest, UpdateWebhookRequest } from '../types/api';

export const useWebhooks = () => {
  return useQuery<Webhook[]>({
    queryKey: ['webhooks'],
    queryFn: () => webhooks.list(),
  });
};

export const useWebhookEvents = () => {
  return useQuery({
    queryKey: ['webhooks', 'events'],
    queryFn: () => webhooks.getEvents(),
  });
};

export const useCreateWebhook = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateWebhookRequest) => webhooks.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
};

export const useUpdateWebhook = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWebhookRequest }) =>
      webhooks.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
};

export const useDeleteWebhook = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => webhooks.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
};

export const useTestWebhook = () => {
  return useMutation({
    mutationFn: (id: string) => webhooks.test(id),
  });
};

export const useWebhookDeliveries = (id: string | null) => {
  return useQuery({
    queryKey: ['webhooks', id, 'deliveries'],
    queryFn: () => webhooks.getDeliveries(id!),
    enabled: !!id,
  });
};
