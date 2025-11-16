import { PageContext } from "vike/types"

export async function data(_: PageContext) {
  const params = new URLSearchParams()
  params.append("player_id", "1")
  const response = await fetch(`http://localhost:8000/api/web/player?${params}`)
  let data = await response.json()
  return data
}
