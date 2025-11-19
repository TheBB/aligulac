import type { PageContext } from "vike/types"

export default async function onBeforeRender(pageContext: PageContext) {
  const isBrowser = typeof window !== "undefined"
  const isDev = import.meta.env.DEV
  const apiBase = isBrowser ? "" : isDev ? "http://localhost:8000" : "http://backend:8000"

  try {
    const response = await fetch(`${apiBase}/api/web/whoami`, {
      headers: { Cookie: pageContext.headers?.cookie ?? "" },
    })
    const data = await response.json()

    return {
      pageContext: {
        username: data.username,
      },
    }
  } catch (_) {
    return {}
  }
}
