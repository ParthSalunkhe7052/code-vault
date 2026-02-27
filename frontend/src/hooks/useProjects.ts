import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projects as projectApi } from '../services/api';
import { Project, CreateProjectRequest, ProjectConfig } from '../types/api';

export const useProjects = () => {
  return useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => projectApi.list(),
  });
};

export const useProjectConfig = (id: string | null) => {
  return useQuery<ProjectConfig>({
    queryKey: ['projects', id, 'config'],
    queryFn: () => projectApi.getConfig(id!),
    enabled: !!id,
  });
};

export const useCreateProject = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateProjectRequest) => projectApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
};

export const useDeleteProject = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => projectApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
};
