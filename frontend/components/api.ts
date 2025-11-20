import type { LoginRequest, LoginResponse, TopTenResponse } from "./models"

const IS_BROWSER = typeof window !== "undefined"
const IS_DEV = import.meta.env.DEV
const API_ROOT = IS_BROWSER
  ? "/api/web"
  : IS_DEV
    ? "http://localhost:8000/api/web"
    : "http://backend:8000/api/web"

type HttpMethod = "GET" | "POST"

const apiRequest = async <I, R>(path: string, method: HttpMethod, body: I): Promise<R> => {
  const response = await fetch(`${API_ROOT}/${path}`, {
    method,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    throw new Error()
  }
  return (await response.json()) as R
}

const get =
  <R>(path: string) =>
  (): Promise<R> =>
    apiRequest<undefined, R>(path, "GET", undefined)
const post =
  <I = undefined, R = undefined>(path: string) =>
  (body: I) =>
    apiRequest<I, R>(path, "POST", body)

export const login = post<LoginRequest, LoginResponse>("login")
export const logout = () => post("logout")(undefined)
export const whoami = get<LoginResponse>("whoami")
export const topTen = get<TopTenResponse>("topten")
