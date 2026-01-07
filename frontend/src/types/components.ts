/**
 * Component Prop Types for CodeVault
 *
 * Reusable prop type definitions for React components.
 */

import { ReactNode, MouseEvent, ChangeEvent, KeyboardEvent, FormEvent } from "react";

// =============================================================================
// Common Props
// =============================================================================

export interface WithChildren {
  children: ReactNode;
}

export interface WithClassName {
  className?: string;
}

export interface WithId {
  id?: string;
}

export interface BaseProps extends WithClassName, WithId {}

// =============================================================================
// Button Props
// =============================================================================

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost" | "outline";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends BaseProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  type?: "button" | "submit" | "reset";
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void;
  children: ReactNode;
}

// =============================================================================
// Input Props
// =============================================================================

export type InputType = "text" | "email" | "password" | "number" | "url" | "search" | "tel";

export interface InputProps extends BaseProps {
  type?: InputType;
  name?: string;
  value?: string | number;
  defaultValue?: string | number;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  autoFocus?: boolean;
  autoComplete?: string;
  maxLength?: number;
  minLength?: number;
  min?: number;
  max?: number;
  step?: number;
  pattern?: string;
  error?: string;
  label?: string;
  helperText?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void;
  onBlur?: (e: ChangeEvent<HTMLInputElement>) => void;
  onFocus?: (e: ChangeEvent<HTMLInputElement>) => void;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
}

export interface TextAreaProps extends BaseProps {
  name?: string;
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  rows?: number;
  maxLength?: number;
  error?: string;
  label?: string;
  helperText?: string;
  onChange?: (e: ChangeEvent<HTMLTextAreaElement>) => void;
  onBlur?: (e: ChangeEvent<HTMLTextAreaElement>) => void;
}

export interface SelectOption<T = string> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SelectProps<T = string> extends BaseProps {
  name?: string;
  value?: T;
  defaultValue?: T;
  options: SelectOption<T>[];
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  error?: string;
  label?: string;
  helperText?: string;
  onChange?: (value: T) => void;
}

// =============================================================================
// Modal Props
// =============================================================================

export interface ModalProps extends WithChildren {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: "sm" | "md" | "lg" | "xl" | "full";
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  showCloseButton?: boolean;
}

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "info";
  isLoading?: boolean;
}

// =============================================================================
// Table Props
// =============================================================================

export interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: string | number;
  sortable?: boolean;
  render?: (item: T, index: number) => ReactNode;
}

export interface TableProps<T> extends BaseProps {
  data: T[];
  columns: Column<T>[];
  keyField: keyof T;
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
  selectedRow?: string | number | null;
  sortColumn?: string;
  sortDirection?: "asc" | "desc";
  onSort?: (column: string) => void;
}

// =============================================================================
// Toast/Notification Props
// =============================================================================

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastProps {
  id: string;
  type: ToastType;
  message: string;
  title?: string;
  duration?: number;
  onClose?: () => void;
}

// =============================================================================
// Form Props
// =============================================================================

export interface FormProps extends BaseProps, WithChildren {
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  loading?: boolean;
}

export interface FormFieldProps extends WithChildren {
  label: string;
  htmlFor?: string;
  error?: string;
  helperText?: string;
  required?: boolean;
}

// =============================================================================
// Card Props
// =============================================================================

export interface CardProps extends BaseProps, WithChildren {
  title?: string;
  subtitle?: string;
  headerAction?: ReactNode;
  footer?: ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
}

// =============================================================================
// Badge/Status Props
// =============================================================================

export type BadgeVariant = "success" | "error" | "warning" | "info" | "neutral";

export interface BadgeProps extends BaseProps {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  children: ReactNode;
}

export interface StatusBadgeProps extends BaseProps {
  status: "active" | "inactive" | "pending" | "error" | "expired" | "revoked";
}

// =============================================================================
// Loading Props
// =============================================================================

export interface SpinnerProps extends BaseProps {
  size?: "sm" | "md" | "lg";
}

export interface SkeletonProps extends BaseProps {
  width?: string | number;
  height?: string | number;
  variant?: "text" | "circular" | "rectangular";
  animation?: "pulse" | "wave" | "none";
}

// =============================================================================
// Layout Props
// =============================================================================

export interface LayoutProps extends WithChildren {
  sidebar?: boolean;
  header?: boolean;
  footer?: boolean;
}

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  actions?: ReactNode;
}

export interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

// =============================================================================
// Empty State Props
// =============================================================================

export interface EmptyStateProps extends BaseProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// =============================================================================
// Dropdown/Menu Props
// =============================================================================

export interface DropdownItem {
  label: string;
  value?: string;
  icon?: ReactNode;
  disabled?: boolean;
  danger?: boolean;
  onClick?: () => void;
}

export interface DropdownProps extends BaseProps {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: "left" | "right";
  width?: string | number;
}

// =============================================================================
// Tabs Props
// =============================================================================

export interface TabItem {
  key: string;
  label: string;
  icon?: ReactNode;
  disabled?: boolean;
  badge?: string | number;
}

export interface TabsProps extends BaseProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (key: string) => void;
  variant?: "underline" | "pills" | "enclosed";
}

// =============================================================================
// Pagination Props
// =============================================================================

export interface PaginationProps extends BaseProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  siblingCount?: number;
  showFirstLast?: boolean;
}

// =============================================================================
// Search Props
// =============================================================================

export interface SearchProps extends BaseProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  debounceMs?: number;
  loading?: boolean;
  onClear?: () => void;
}

// =============================================================================
// File Upload Props
// =============================================================================

export interface FileUploadProps extends BaseProps {
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // bytes
  maxFiles?: number;
  disabled?: boolean;
  onFilesSelected: (files: File[]) => void;
  onError?: (error: string) => void;
}

// =============================================================================
// Chart Props
// =============================================================================

export interface ChartDataPoint {
  name: string;
  value: number;
  [key: string]: unknown;
}

export interface LineChartProps extends BaseProps {
  data: ChartDataPoint[];
  xKey: string;
  yKey: string;
  height?: number;
  color?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
}

export interface BarChartProps extends BaseProps {
  data: ChartDataPoint[];
  xKey: string;
  yKey: string;
  height?: number;
  color?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
}
