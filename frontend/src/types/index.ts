/* Shared TypeScript interfaces matching backend schemas */

export enum EventType {
  sensor = 'sensor',
  actuator = 'actuator',
  range = 'range',
  cmd_button = 'cmd_button',
  cmd_opened = 'cmd_opened',
  cmd_closed = 'cmd_closed',
}

export enum LoggingType {
  info = 'info',
  warning = 'warning',
  error = 'error',
}

export type UserRole = 'admin' | 'operator' | 'viewer'

export interface StatusResponse {
  status: string
  message: string
}

export interface User {
  public_id: string
  email: string
  username: string
  role: UserRole
  admin: boolean
  registered_on: string
}

export interface Event {
  public_id: string
  name: string
  min_value: number
  max_value: number
  unit: string
  type: EventType
  user_public_id: string | null
}

export interface Experiment {
  public_id: string
  name: string
  started_on: string | null
  stopped_on: string | null
  user_public_id: string | null
}

export interface Datapoint {
  public_id: string
  value: number
  timestamp: string | null
  event_public_id: string
  experiment_public_id: string | null
}

export enum StatusType {
  read = 'read',
  unread = 'unread',
}

export interface LogEntry {
  public_id: string
  content: string
  logging_type: LoggingType | null
  status_type: StatusType | null
  created_on: string | null
  user_public_id: string
}

export interface PaginatedResponse<T> {
  page: number
  page_size: number
  total: number
  data: T[]
}

export interface LoginResponse {
  status: string
  message: string
  access_token: string
  public_id: string
  username: string
}

// Webhook types
export type WebhookEventType =
  | 'sensor.threshold_exceeded'
  | 'sensor.reading'
  | 'experiment.started'
  | 'experiment.stopped'
  | 'system.health_changed'

export interface Webhook {
  public_id: string
  url: string
  events: WebhookEventType[]
  enabled: boolean
  created_on: string
  user_public_id: string
}

export interface WebhookCreatePayload {
  url: string
  secret?: string | null
  events: WebhookEventType[]
  enabled: boolean
}

export interface WebhookUpdatePayload {
  url?: string
  secret?: string | null
  events?: WebhookEventType[]
  enabled?: boolean
}

// Rule types
export type RuleOperator = 'gt' | 'lt' | 'gte' | 'lte' | 'eq' | 'between' | 'not_between'
export type RuleActionType = 'webhook' | 'log'

export interface Rule {
  public_id: string
  name: string
  event_public_id: string
  operator: RuleOperator
  threshold: number
  threshold_high: number | null
  action_type: RuleActionType
  webhook_event_type: string | null
  enabled: boolean
  cooldown_seconds: number
  last_triggered_at: string | null
  created_on: string
  user_public_id: string
}

// OTA types
export type UpdateStatus =
  | 'pending'
  | 'downloading'
  | 'verifying'
  | 'applying'
  | 'completed'
  | 'failed'
  | 'rolled_back'

export interface FirmwareUpdate {
  public_id: string
  version: string
  changelog: string | null
  has_firmware_file: boolean
  file_hash_sha256: string | null
  file_size_bytes: number | null
  status: UpdateStatus
  error_message: string | null
  created_on: string
  started_on: string | null
  completed_on: string | null
  user_public_id: string
}

export interface UpdateCheckResponse {
  current_version: string
  latest_version: string | null
  update_available: boolean
  github_latest_version: string | null
  github_download_url: string | null
  github_release_url: string | null
  github_error: string | null
}

// Dashboard types
export type WidgetType = 'line_chart' | 'gauge' | 'stat_card' | 'actuator_toggle'

export interface DashboardWidget {
  public_id: string
  widget_type: WidgetType
  title: string
  event_public_id: string | null
  x: number
  y: number
  w: number
  h: number
  config_json: string | null
}

export interface Dashboard {
  public_id: string
  name: string
  is_global: boolean
  created_on: string
  user_public_id: string
  widgets: DashboardWidget[]
}

export interface DashboardCreatePayload {
  name: string
  is_global: boolean
}

export interface DashboardWidgetCreatePayload {
  widget_type: WidgetType
  title: string
  event_public_id?: string | null
  x?: number
  y?: number
  w: number
  h: number
  config_json?: string | null
}

// Plugin types
export type PluginStatus = 'inactive' | 'connected' | 'error' | 'demo'
export type ChannelDirection = 'input' | 'output' | 'bidirectional'

export interface PluginMeta {
  id: string
  name: string
  version: string
  vendor: string
  description: string
  url: string | null
}

export interface ChannelMapping {
  public_id: string
  channel_id: string
  channel_name: string
  direction: ChannelDirection
  unit: string
  event_public_id: string | null
  created_on: string | null
}

export interface PluginInstance {
  public_id: string
  plugin_id: string
  instance_name: string
  demo_mode: boolean
  enabled: boolean
  status: PluginStatus
  config_json: string | null
  error_message: string | null
  created_on: string | null
  updated_on: string | null
  user_public_id: string
  channel_mappings: ChannelMapping[]
}

export interface PluginInstanceCreatePayload {
  plugin_id: string
  instance_name: string
  demo_mode: boolean
  enabled: boolean
  auto_create_events: boolean
  config_json?: string | null
}

export interface PluginInstanceUpdatePayload {
  instance_name?: string
  demo_mode?: boolean
  enabled?: boolean
  config_json?: string | null
}

export interface ChannelMappingUpdatePayload {
  event_public_id: string | null
}

// Plugin packages
export type PluginSourceType = 'bundled' | 'uploaded'

export interface PluginPackage {
  public_id: string
  package_name: string
  version: string
  source: PluginSourceType
  plugin_ids: string[]
  file_size_bytes: number | null
  installed_on: string | null
  removable: boolean
}

// API Token types
export interface ApiToken {
  public_id: string
  name: string
  last_used_at: string | null
  expires_at: string | null
  created_at: string
  user_public_id: string
}

export interface ApiTokenCreated extends ApiToken {
  token: string
}

export interface ApiTokenCreatePayload {
  name: string
  expires_at?: string | null
}
