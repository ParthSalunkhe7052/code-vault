/**
 * Core API Type Definitions for CodeVault
 *
 * These types mirror the backend Pydantic models and API responses.
 */

// =============================================================================
// Authentication Types
// =============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  tier: "free" | "pro" | "enterprise";
  stripe_customer_id: string | null;
  api_key: string;
  created_at: string;
  updated_at?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  user: User;
}

// =============================================================================
// Project Types
// =============================================================================

export interface Project {
  id: string;
  name: string;
  description?: string;
  language: "python" | "nodejs";
  entry_file: string;
  output_name: string;
  user_id: string;
  created_at: string;
  updated_at?: string;
  file_count?: number;
  license_count?: number;
}

export interface ProjectConfig {
  entry_file: string;
  output_name: string;
  language: "python" | "nodejs";
  license_key?: string;
  server_url?: string;
  lease_enabled?: boolean;
  obfuscate_enabled?: boolean;
  nuitka_options?: NuitkaOptions;
  compiler_options?: CompilerOptions;
}

export interface NuitkaOptions {
  include_packages?: string[];
  enable_plugins?: string[];
  extra_args?: string[];
}

export interface CompilerOptions {
  target?: string; // e.g., "node18-win-x64"
}

export interface ProjectFile {
  id: string;
  project_id: string;
  filename: string;
  path: string;
  size: number;
  created_at: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  language: "python" | "nodejs";
  entry_file?: string;
  output_name?: string;
}

// =============================================================================
// License Types
// =============================================================================

export interface License {
  id: string;
  project_id: string;
  project_name?: string;
  license_key: string;
  status: "active" | "revoked" | "expired";
  expires_at: string | null;
  max_machines: number;
  features: string[];
  client_name?: string;
  client_email?: string;
  notes?: string;
  created_at: string;
  active_machines: number;
}

export interface CreateLicenseRequest {
  project_id: string;
  expires_at?: string | null;
  max_machines?: number;
  features?: string[];
  client_name?: string;
  client_email?: string;
  notes?: string;
}

export interface HardwareBinding {
  id: string;
  hwid: string;
  machine_name?: string;
  ip_address?: string;
  first_seen_at: string;
  last_seen_at: string;
  is_active: boolean;
}

export interface LicenseValidationRequest {
  license_key: string;
  hwid: string;
  machine_name?: string;
  nonce: string;
  timestamp: number;
}

export interface LicenseValidationResponse {
  status: "valid" | "invalid" | "expired" | "revoked" | "hwid_mismatch";
  message: string;
  expires_at?: number;
  features?: string[];
  nonce: string;
  signature: string;
}

// =============================================================================
// Webhook Types
// =============================================================================

export type WebhookEvent =
  | "license.created"
  | "license.validated"
  | "license.revoked"
  | "license.expired"
  | "hwid.bound"
  | "hwid.reset"
  | "compilation.started"
  | "compilation.completed"
  | "compilation.failed";

export interface Webhook {
  id: string;
  name: string;
  url: string;
  events: WebhookEvent[];
  secret?: string;
  is_active: boolean;
  last_triggered_at: string | null;
  failure_count: number;
  created_at: string;
}

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  response_status: number;
  response_body?: string;
  delivery_time_ms: number;
  success: boolean;
  created_at: string;
}

export interface CreateWebhookRequest {
  name: string;
  url: string;
  events: WebhookEvent[];
  secret?: string;
}

export interface UpdateWebhookRequest {
  name?: string;
  url?: string;
  events?: WebhookEvent[];
  secret?: string;
  is_active?: boolean;
}

// =============================================================================
// Build/Compilation Types
// =============================================================================

export type BuildStatus =
  | "pending"
  | "compiling"
  | "uploading"
  | "completed"
  | "failed";

export interface BuildJob {
  id: string;
  project_id: string;
  status: BuildStatus;
  progress: number;
  message?: string;
  output_url?: string;
  output_filename?: string;
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface BuildPrerequisites {
  python: {
    installed: boolean;
    version?: string;
    path?: string;
  };
  nuitka: {
    installed: boolean;
    version?: string;
  };
  nodejs: {
    installed: boolean;
    version?: string;
    path?: string;
  };
  pkg: {
    installed: boolean;
    version?: string;
  };
}

// =============================================================================
// Analytics/Stats Types
// =============================================================================

export interface DashboardStats {
  total_projects: number;
  total_licenses: number;
  active_licenses: number;
  total_validations: number;
  validations_today: number;
  validations_this_week: number;
  recent_activity: ActivityItem[];
}

export interface ActivityItem {
  type: "license_created" | "validation" | "build_completed" | "webhook_triggered";
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface ValidationStats {
  date: string;
  valid: number;
  invalid: number;
  expired: number;
  revoked: number;
  hwid_mismatch: number;
}

export interface GeographicData {
  country: string;
  city?: string;
  count: number;
  latitude?: number;
  longitude?: number;
}

export interface MapDataPoint {
  id: string;
  latitude: number;
  longitude: number;
  city?: string;
  country: string;
  license_key?: string;
  result: string;
  timestamp: string;
}

// =============================================================================
// Admin Types
// =============================================================================

export interface AdminStats {
  total_users: number;
  total_projects: number;
  total_licenses: number;
  total_validations: number;
  revenue_mtd: number;
  active_subscriptions: number;
  users_by_tier: Record<string, number>;
}

export interface AdminUser extends User {
  projects_count: number;
  licenses_count: number;
  last_login?: string;
}

// =============================================================================
// Subscription/Billing Types
// =============================================================================

export interface SubscriptionStatus {
  tier: "free" | "pro" | "enterprise";
  status: "active" | "canceled" | "past_due" | "trialing" | null;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
  stripe_customer_id?: string;
}

export interface PricingTier {
  id: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
  limits: TierLimits;
  stripe_price_id_monthly: string;
  stripe_price_id_yearly: string;
}

export interface TierLimits {
  max_projects: number; // -1 for unlimited
  max_licenses_per_project: number; // -1 for unlimited
  webhooks: boolean;
  priority_support: boolean;
  custom_branding: boolean;
  api_access: boolean;
}

// =============================================================================
// API Response Types
// =============================================================================

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

// =============================================================================
// Settings Types
// =============================================================================

export interface UserSettings {
  theme: "light" | "dark" | "system";
  notifications_enabled: boolean;
  email_notifications: boolean;
  webhook_retry_enabled: boolean;
  default_license_duration_days: number;
  default_max_machines: number;
}

export interface BuildSettings {
  default_language: "python" | "nodejs";
  default_target: string;
  obfuscation_enabled: boolean;
  auto_upload: boolean;
}
