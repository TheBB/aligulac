import createFetchClient from "openapi-fetch"
import createClient from "openapi-react-query"
import type { components, paths } from "./models"

const IS_BROWSER = typeof window !== "undefined"
const IS_DEV = import.meta.env.DEV
const API_ROOT = IS_BROWSER ? "/" : IS_DEV ? "http://localhost:8000/" : "http://backend:8000/"

const fetchClient = createFetchClient<paths>({ baseUrl: API_ROOT })

export const login = async (request: components["schemas"]["LoginRequest"]) =>
  await fetchClient.POST("/api/web/login", { body: request })
export const logout = async () => await fetchClient.POST("/api/web/logout")
export const whoami = async () => await fetchClient.GET("/api/web/whoami")

const api = createClient(fetchClient)

export const useTopTen = () => {
  return api.useSuspenseQuery("get", "/api/web/topten")
}

export const useRecentBlog = () => {
  return api.useSuspenseQuery("get", "/api/web/blog", { params: { query: { limit: 3 } } })
}
