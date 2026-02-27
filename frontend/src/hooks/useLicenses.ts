import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { licenses as licenseApi } from '../services/api';
import { License, CreateLicenseRequest, HardwareBinding } from '../types/api';

export const useLicenses = (projectId?: string) => {
  return useQuery<License[]>({
    queryKey: ['licenses', projectId],
    queryFn: () => licenseApi.list(projectId!),
  });
};

export const useCreateLicense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateLicenseRequest) => licenseApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['licenses'] });
    },
  });
};

export const useRevokeLicense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => licenseApi.revoke(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['licenses'] });
    },
  });
};

export const useDeleteLicense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => licenseApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['licenses'] });
    },
  });
};

export const useLicenseBindings = (id: string | null) => {
  return useQuery<HardwareBinding[]>({
    queryKey: ['licenses', id, 'bindings'],
    queryFn: () => licenseApi.getBindings(id!),
    enabled: !!id,
  });
};

export const useLicenseResetStatus = (id: string | null) => {
  return useQuery({
    queryKey: ['licenses', id, 'reset-status'],
    queryFn: () => licenseApi.getResetStatus(id!),
    enabled: !!id,
  });
};
