import { useQuery } from '@tanstack/react-query';
import { stats, projects } from '../services/api';
import { DashboardStats, Project } from '../types/api';

export const useDashboardStats = () => {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => stats.getDashboard(),
  });
};

export const useProjects = () => {
  return useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => projects.list(),
  });
};
