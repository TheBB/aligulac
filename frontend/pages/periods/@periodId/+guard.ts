import { render } from "vike/abort"
import type { PageContext } from "vike/types"

export const guard = async (pageContext: PageContext) => {
  const { periodId } = pageContext.routeParams
  if (periodId !== "latest" && Number.isNaN(+periodId)) {
    throw render(404, "Incorrect periodId")
  }
}
