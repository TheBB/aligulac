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

export const periodUrl = (periodId: number): string => {
  return `periods/${periodId}`
}

export const renderDate = (date: string): string => {
  return format(parse(date, "yyyy-MM-dd", new Date()), "MMM d, yyyy")
}
