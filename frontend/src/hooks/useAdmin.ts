import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { admin } from '../services/api';
import { AdminStats, AdminUser } from '../types/api';

export const useAdminStats = () => {
  return useQuery<AdminStats>({
    queryKey: ['admin', 'stats'],
    queryFn: () => admin.getStats(),
  });
};

export const useAdminUsers = () => {
  return useQuery<AdminUser[]>({
    queryKey: ['admin', 'users'],
    queryFn: () => admin.getUsers(),
  });
};

export const useAdminAnalytics = (days: number = 30) => {
  return useQuery({
    queryKey: ['admin', 'analytics', days],
    queryFn: () => admin.getAnalytics(days),
  });
};

export const useAdminRevenue = () => {
  return useQuery({
    queryKey: ['admin', 'revenue'],
    queryFn: () => admin.getRevenue(),
    retry: false, // Revenue might not be available for all setups
  });
};

export const useAdminSystemHealth = () => {
  return useQuery({
    queryKey: ['admin', 'health'],
    queryFn: () => admin.getSystemHealth(),
    refetchInterval: 30000, // Refresh health every 30s
    retry: false,
  });
};

export const useUpdateUserPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, plan }: { userId: string; plan: string }) =>
      admin.updateUserPlan(userId, plan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
  });
};

export const useUpdateUserRole = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      admin.updateUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
  });
};

export const useBanUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => admin.banUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
  });
};
