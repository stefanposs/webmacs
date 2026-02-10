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
  debug = 'debug',
}

export interface StatusResponse {
  status: string
  message: string
}

export interface User {
  public_id: string
  email: string
  username: string
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

export interface LogEntry {
  public_id: string
  content: string
  logging_type: string | null
  status_type: string | null
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
