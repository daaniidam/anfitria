import type {
  Conversation,
  InboundResult,
  InboxItem,
  KnowledgeItem,
  Message,
  Metrics,
  Property,
  User,
} from '../types'
import { api } from './client'

export const MetricsApi = {
  get: () => api<Metrics>('/metrics'),
}

export const AuthApi = {
  register: (body: { email: string; name: string; password: string }) =>
    api<User>('/auth/register', { method: 'POST', body, auth: false }),
  login: (body: { email: string; password: string }) =>
    api<{ access_token: string }>('/auth/login', { method: 'POST', body, auth: false }),
  me: () => api<User>('/auth/me'),
}

export const PropertiesApi = {
  list: () => api<Property[]>('/properties'),
  create: (body: {
    name: string
    address?: string
    default_language: string
    auto_answer?: boolean
  }) => api<Property>('/properties', { method: 'POST', body }),
  knowledge: (propertyId: number) =>
    api<KnowledgeItem[]>(`/properties/${propertyId}/knowledge`),
  addKnowledge: (propertyId: number, body: { category: string; content: string }) =>
    api<KnowledgeItem>(`/properties/${propertyId}/knowledge`, { method: 'POST', body }),
}

export const InboxApi = {
  list: () => api<InboxItem[]>('/inbox'),
  approve: (draftId: number, editedText: string | null) =>
    api<Message>(`/drafts/${draftId}/approve`, {
      method: 'POST',
      body: { edited_text: editedText },
    }),
}

export const ConversationsApi = {
  list: () => api<Conversation[]>('/conversations'),
  inbound: (body: { property_id: number; guest_ref: string; text: string }) =>
    api<InboundResult>('/channels/sim/inbound', { method: 'POST', body }),
  messages: (conversationId: number) =>
    api<Message[]>(`/conversations/${conversationId}/messages`),
}
