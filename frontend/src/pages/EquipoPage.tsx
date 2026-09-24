import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { OrgApi } from '../api/endpoints'
import { useAuth } from '../auth'
import { Button, Card, ConfirmButton, Field, Tag } from '../components/ui'
import { notify } from '../components/Toast'
import type { User } from '../types'

export function EquipoPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner'
  const queryClient = useQueryClient()

  const { data: org } = useQuery({ queryKey: ['org'], queryFn: OrgApi.get })
  const { data: members } = useQuery({ queryKey: ['members'], queryFn: OrgApi.members })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['members'] })

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const invite = useMutation({
    mutationFn: () => OrgApi.invite({ name, email, password, role: 'member' }),
    onSuccess: () => {
      setName('')
      setEmail('')
      setPassword('')
      notify('Miembro añadido al equipo.', 'success')
      void invalidate()
    },
  })
  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => OrgApi.setRole(id, role),
    onSuccess: () => invalidate(),
  })
  const remove = useMutation({
    mutationFn: (id: number) => OrgApi.remove(id),
    onSuccess: () => invalidate(),
  })

  const valid = name.trim() && email.trim() && password.length >= 8

  function onInvite(event: FormEvent) {
    event.preventDefault()
    if (valid) invite.mutate()
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="flex flex-col gap-4">
        <header>
          <p className="eyebrow text-brand-ink">{org?.name ?? 'Tu equipo'}</p>
          <h1 className="mt-1 font-display text-2xl font-bold text-ink">Equipo</h1>
          <p className="mt-1 text-sm text-muted">
            Varias personas comparten la misma cartera de pisos. El propietario gestiona
            el equipo; los miembros operan (responden, editan fichas) pero no borran pisos.
          </p>
        </header>

        <ul className="flex flex-col gap-2">
          {members?.map((member: User) => (
            <li key={member.id}>
              <Card className="flex flex-wrap items-center gap-x-4 gap-y-2 p-3.5">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ink">{member.name}</span>
                    <Tag tone={member.role === 'owner' ? 'brand' : 'muted'}>
                      {member.role === 'owner' ? 'propietario' : 'miembro'}
                    </Tag>
                    {member.id === user?.id ? <span className="text-xs text-muted">(tú)</span> : null}
                  </div>
                  <p className="mt-0.5 text-sm text-muted">{member.email}</p>
                </div>
                {isOwner && member.id !== user?.id ? (
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() =>
                        setRole.mutate({
                          id: member.id,
                          role: member.role === 'owner' ? 'member' : 'owner',
                        })
                      }
                      className="text-xs font-medium text-brand-ink hover:underline"
                    >
                      {member.role === 'owner' ? 'Hacer miembro' : 'Hacer propietario'}
                    </button>
                    <ConfirmButton
                      onConfirm={() => remove.mutate(member.id)}
                      label="Quitar"
                      question="¿Quitar del equipo?"
                    />
                  </div>
                ) : null}
              </Card>
            </li>
          ))}
        </ul>
      </div>

      {isOwner ? (
        <Card className="h-fit p-4">
          <p className="eyebrow mb-3 block text-brand-ink">Invitar a alguien</p>
          <form onSubmit={onInvite} className="flex flex-col gap-3">
            <Field label="Nombre" placeholder="p. ej. Marta" value={name} onChange={(e) => setName(e.target.value)} />
            <Field label="Email" placeholder="marta@empresa.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Field
              label="Contraseña temporal"
              placeholder="mínimo 8 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button variant="brand" type="submit" disabled={!valid || invite.isPending}>
              {invite.isPending ? 'Invitando…' : 'Añadir al equipo'}
            </Button>
            {invite.isError ? (
              <p className="text-xs text-warn">{(invite.error as Error).message}</p>
            ) : null}
          </form>
        </Card>
      ) : (
        <Card className="h-fit p-4">
          <p className="text-sm text-muted">
            Solo el propietario de la cuenta puede invitar o gestionar al equipo.
          </p>
        </Card>
      )}
    </div>
  )
}
