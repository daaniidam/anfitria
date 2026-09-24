export interface User {
  id: number
  email: string
  name: string
  role: string
  org_id: number | null
}

export interface Org {
  id: number
  name: string
}

export interface OnboardingStatus {
  has_property: boolean
  has_knowledge: boolean
  has_whatsapp: boolean
  has_conversation: boolean
}

export interface Building {
  id: number
  name: string
}

export interface Property {
  id: number
  name: string
  address: string | null
  default_language: string
  auto_answer: boolean
  building_id: number | null
}

export interface KnowledgeItem {
  id: number
  category: string
  content: string
}

export interface Message {
  id: number
  direction: 'in' | 'out'
  text: string
  language: string
  created_at: string
}

export interface Draft {
  id: number
  inbound_message_id: number
  text: string
  language: string
  confidence: number
  model: string
  status: string
}

export interface Conversation {
  id: number
  property_id: number
  guest_ref: string
  channel: string
  reservation_id: number | null
  handoff: boolean
  assigned_to: number | null
}

export interface InboundResult {
  conversation: Conversation
  inbound: Message
  draft: Draft
  answered: boolean
}

export interface InboxItem {
  draft: Draft
  inbound_text: string
  guest_ref: string
  conversation_id: number
  property_id: number
  property_name: string
}

export interface MetricsPoint {
  date: string
  auto_answered: number
  escalated: number
}

export interface Metrics {
  properties: number
  conversations: number
  messages_in: number
  messages_out: number
  auto_answered: number
  escalated: number
  pending: number
  auto_rate: number
  minutes_saved: number
  daily: MetricsPoint[]
}

export interface Reservation {
  id: number
  property_id: number
  guest_name: string
  guest_ref: string
  check_in: string
  check_out: string
  status: string
  source: string
  code: string | null
}

export interface ReservationListItem extends Reservation {
  property_name: string
}

export interface Notification {
  id: number
  kind: string
  message: string
  read: boolean
  conversation_id: number | null
  created_at: string
}

export interface AuditLog {
  id: number
  actor: string
  action: string
  detail: string | null
  conversation_id: number | null
  created_at: string
}
