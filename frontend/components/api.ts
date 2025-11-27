import { useSuspenseInfiniteQuery } from "@tanstack/react-query"
import createFetchClient from "openapi-fetch"
import createClient from "openapi-react-query"
import type { components, paths } from "./models"

type BlogResponse = components["schemas"]["BlogResponse"]

const IS_BROWSER = typeof window !== "undefined"
const IS_DEV = import.meta.env.DEV
const API_ROOT = IS_BROWSER ? "/" : IS_DEV ? "http://localhost:8000/" : "http://backend:8000/"

const fetchClient = createFetchClient<paths>({ baseUrl: API_ROOT })

export const login = async (request: components["schemas"]["LoginRequest"]) =>
  await fetchClient.POST("/api/web/login", { body: request })
export const logout = async () => await fetchClient.POST("/api/web/logout")
export const whoami = async () => await fetchClient.GET("/api/web/whoami")

const api = createClient(fetchClient)

interface UseRatingListOptions {
  offset?: number
  limit?: number
}

export const useRatingList = (periodId: number | "latest", options: UseRatingListOptions) => {
  const limit = options?.limit ?? 40
  const offset = options?.offset ?? 0
  return api.useSuspenseQuery("get", "/api/web/ratinglist", {
    params: { query: { limit, offset, period_id: periodId } },
  })
}

export const useTopTen = () => {
  return api.useSuspenseQuery("get", "/api/web/topten")
}

export const useRecentBlog = () => {
  return api.useSuspenseQuery("get", "/api/web/blog", { params: { query: { limit: 3 } } })
}

export const useInfiniteBlog = () => {
  return useSuspenseInfiniteQuery({
    queryKey: ["blog"],
    queryFn: async ({ pageParam }) => {
      const { data, error } = await fetchClient.GET("/api/web/blog", {
        params: { query: { limit: 10, offset: pageParam } },
      })
      if (error) throw error
      return data
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage: BlogResponse) => lastPage.next_offset,
  })
}
