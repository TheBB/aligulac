import type { PageContext } from "vike/types"
import { LoginResponse } from "../components/models"
import { computeApiBase } from "../components/Api"

export default async function onBeforeRender(pageContext: PageContext) {
  const apiBase = computeApiBase()

  try {
    const response = await fetch(`${apiBase}/whoami`, {
      headers: { Cookie: pageContext.headers?.cookie ?? "" },
    })
    const data = await response.json() as LoginResponse

    return {
      pageContext: {
        username: data.username,
      },
    }
  } catch (_) {
    return {}
  }
}
