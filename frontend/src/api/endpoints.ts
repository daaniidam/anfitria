import type {
  AuditLog,
  Building,
  Conversation,
  InboundResult,
  InboxItem,
  KnowledgeItem,
  Message,
  Metrics,
  Notification,
  Org,
  Property,
  Reservation,
  User,
} from '../types'
import { api, apiUpload } from './client'

export const BuildingsApi = {
  list: () => api<Building[]>('/buildings'),
  create: (body: { name: string }) => api<Building>('/buildings', { method: 'POST', body }),
  remove: (id: number) => api<void>(`/buildings/${id}`, { method: 'DELETE' }),
  knowledge: (id: number) => api<KnowledgeItem[]>(`/buildings/${id}/knowledge`),
  addKnowledge: (id: number, body: { category: string; content: string }) =>
    api<KnowledgeItem>(`/buildings/${id}/knowledge`, { method: 'POST', body }),
  updateKnowledge: (id: number, itemId: number, body: { category?: string; content?: string }) =>
    api<KnowledgeItem>(`/buildings/${id}/knowledge/${itemId}`, { method: 'PATCH', body }),
  removeKnowledge: (id: number, itemId: number) =>
    api<void>(`/buildings/${id}/knowledge/${itemId}`, { method: 'DELETE' }),
}

export const MetricsApi = {
  get: () => api<Metrics>('/metrics'),
}

export const NotificationsApi = {
  list: () => api<Notification[]>('/notifications'),
  unreadCount: () => api<{ count: number }>('/notifications/unread-count'),
  markRead: (id: number) => api<void>(`/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => api<void>('/notifications/read-all', { method: 'POST' }),
}

export const AuditApi = {
  list: () => api<AuditLog[]>('/audit'),
}

export const OrgApi = {
  get: () => api<Org>('/org'),
  members: () => api<User[]>('/org/members'),
  invite: (body: { email: string; name: string; password: string; role?: string }) =>
    api<User>('/org/members', { method: 'POST', body }),
  setRole: (id: number, role: string) =>
    api<User>(`/org/members/${id}`, { method: 'PATCH', body: { role } }),
  remove: (id: number) => api<void>(`/org/members/${id}`, { method: 'DELETE' }),
}

export const AuthApi = {
  register: (body: { email: string; name: string; password: string }) =>
    api<User>('/auth/register', { method: 'POST', body }),
  login: (body: { email: string; password: string }) =>
    api<{ access_token: string }>('/auth/login', { method: 'POST', body }),
  logout: () => api<void>('/auth/logout', { method: 'POST' }),
  me: () => api<User>('/auth/me'),
}

export const PropertiesApi = {
  list: () => api<Property[]>('/properties'),
  create: (body: {
    name: string
    address?: string
    default_language: string
    auto_answer?: boolean
    building_id?: number | null
  }) => api<Property>('/properties', { method: 'POST', body }),
  remove: (id: number) => api<void>(`/properties/${id}`, { method: 'DELETE' }),
  knowledge: (propertyId: number) =>
    api<KnowledgeItem[]>(`/properties/${propertyId}/knowledge`),
  addKnowledge: (propertyId: number, body: { category: string; content: string }) =>
    api<KnowledgeItem>(`/properties/${propertyId}/knowledge`, { method: 'POST', body }),
  importKnowledge: (propertyId: number, file: File) =>
    apiUpload<{ imported: number }>(`/properties/${propertyId}/knowledge/import`, file),
  updateKnowledge: (
    propertyId: number,
    itemId: number,
    body: { category?: string; content?: string },
  ) =>
    api<KnowledgeItem>(`/properties/${propertyId}/knowledge/${itemId}`, {
      method: 'PATCH',
      body,
    }),
  removeKnowledge: (propertyId: number, itemId: number) =>
    api<void>(`/properties/${propertyId}/knowledge/${itemId}`, { method: 'DELETE' }),
}

export const ReservationsApi = {
  list: () => api<Reservation[]>('/reservations'),
  byProperty: (propertyId: number) =>
    api<Reservation[]>(`/properties/${propertyId}/reservations`),
  create: (
    propertyId: number,
    body: {
      guest_name: string
      guest_ref: string
      check_in: string
      check_out: string
      code?: string | null
    },
  ) => api<Reservation>(`/properties/${propertyId}/reservations`, { method: 'POST', body }),
  update: (id: number, body: Partial<{ status: string; check_in: string; check_out: string }>) =>
    api<Reservation>(`/reservations/${id}`, { method: 'PATCH', body }),
  remove: (id: number) => api<void>(`/reservations/${id}`, { method: 'DELETE' }),
}

export const InboxApi = {
  list: () => api<InboxItem[]>('/inbox'),
  approve: (draftId: number, editedText: string | null, saveToKnowledge: boolean) =>
    api<Message>(`/drafts/${draftId}/approve`, {
      method: 'POST',
      body: { edited_text: editedText, save_to_knowledge: saveToKnowledge },
    }),
}

export const ConversationsApi = {
  list: () => api<Conversation[]>('/conversations'),
  inbound: (body: { property_id: number; guest_ref: string; text: string }) =>
    api<InboundResult>('/channels/sim/inbound', { method: 'POST', body }),
  messages: (conversationId: number) =>
    api<Message[]>(`/conversations/${conversationId}/messages`),
}
