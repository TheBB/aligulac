import { format, parse } from "date-fns"

const filterUrl = (name: string): string => {
  return encodeURIComponent(name.replaceAll(" ", "-").replaceAll("/", ""))
}

export const playerUrl = ({ id, tag }: { id: number; tag: string }): string => {
  return `/players/${id}-${filterUrl(tag)}`
}

export const playerPeriodUrl = (player: { id: number; tag: string }, periodId: number): string => {
  return `${playerUrl(player)}/period/${periodId}`
}

interface PeriodUrlOptions {
  page?: number
  sort?: "vp" | "vt" | "vz"
  nats?: string
  race?: string
}

export const periodUrl = (periodId: number | "latest", options?: PeriodUrlOptions): string => {
  const base = `/periods/${periodId}`
  const params = new URLSearchParams()
  const { page, sort, nats, race } = options ?? {}

  if (page !== undefined) {
    params.append("page", page.toString())
  }

  if (sort !== undefined) {
    params.append("sort", sort)
  }

  if (nats !== undefined) {
    params.append("nats", nats)
  }

  if (race !== undefined) {
    params.append("race", race)
  }

  if (params.size === 0) {
    return base
  }
  return `${base}?${params.toString()}`
}

export const renderDate = (date: string): string => {
  return format(parse(date, "yyyy-MM-dd", new Date()), "MMM d, yyyy")
}
