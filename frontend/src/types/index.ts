/**
 * Type Definitions Index for CodeVault Frontend
 *
 * Re-exports all type definitions for convenient imports.
 *
 * Usage:
 *   import type { User, Project, License } from '@/types';
 *   import type { ButtonProps, ModalProps } from '@/types';
 */

// API Types
export type {
  // Auth
  User,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  // Projects
  Project,
  ProjectConfig,
  ProjectFile,
  NuitkaOptions,
  CompilerOptions,
  CreateProjectRequest,
  // Licenses
  License,
  CreateLicenseRequest,
  HardwareBinding,
  LicenseValidationRequest,
  LicenseValidationResponse,
  // Webhooks
  WebhookEvent,
  Webhook,
  WebhookDelivery,
  CreateWebhookRequest,
  UpdateWebhookRequest,
  // Builds
  BuildStatus,
  BuildJob,
  BuildPrerequisites,
  // Analytics
  DashboardStats,
  ActivityItem,
  ValidationStats,
  GeographicData,
  MapDataPoint,
  // Admin
  AdminStats,
  AdminUser,
  // Billing
  SubscriptionStatus,
  PricingTier,
  TierLimits,
  // Common
  ApiError,
  PaginatedResponse,
  // Settings
  UserSettings,
  BuildSettings,
} from "./api";

// Component Props Types
export type {
  // Common
  WithChildren,
  WithClassName,
  WithId,
  BaseProps,
  // Button
  ButtonVariant,
  ButtonSize,
  ButtonProps,
  // Input
  InputType,
  InputProps,
  TextAreaProps,
  SelectOption,
  SelectProps,
  // Modal
  ModalProps,
  ConfirmDialogProps,
  // Table
  Column,
  TableProps,
  // Toast
  ToastType,
  ToastProps,
  // Form
  FormProps,
  FormFieldProps,
  // Card
  CardProps,
  // Badge
  BadgeVariant,
  BadgeProps,
  StatusBadgeProps,
  // Loading
  SpinnerProps,
  SkeletonProps,
  // Layout
  LayoutProps,
  PageHeaderProps,
  SidebarProps,
  // Empty State
  EmptyStateProps,
  // Dropdown
  DropdownItem,
  DropdownProps,
  // Tabs
  TabItem,
  TabsProps,
  // Pagination
  PaginationProps,
  // Search
  SearchProps,
  // File Upload
  FileUploadProps,
  // Charts
  ChartDataPoint,
  LineChartProps,
  BarChartProps,
} from "./components";
