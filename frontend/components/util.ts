import { format, parse } from "date-fns"

// import { URLSearchParams } from "url";

const filterUrl = (name: string): string => {
  return encodeURIComponent(name.replaceAll(" ", "-").replaceAll("/", ""))
}

export const playerUrl = ({ id, tag }: { id: number; tag: string }): string => {
  return `/players/${id}-${filterUrl(tag)}`
}

export const playerPeriodUrl = (player: { id: number; tag: string }, periodId: number): string => {
  return `${playerUrl(player)}/period/${periodId}`
}

export const periodUrl = (
  periodId: number | "latest",
  page?: number,
  sort?: "vp" | "vt" | "vz",
  nationality?: string,
): string => {
  const base = `/periods/${periodId}`
  const params = new URLSearchParams()

  if (page !== undefined) {
    params.append("page", page.toString())
  }

  if (sort !== undefined) {
    params.append("sort", sort)
  }

  if (nationality !== undefined) {
    params.append("nats", nationality)
  }

  if (params.size === 0) {
    return base
  }
  return `${base}?${params.toString()}`
}

export const renderDate = (date: string): string => {
  return format(parse(date, "yyyy-MM-dd", new Date()), "MMM d, yyyy")
}
