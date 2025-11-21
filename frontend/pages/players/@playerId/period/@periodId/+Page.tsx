import { usePageContext } from "vike-react/usePageContext";

export default function Page() {
  const pageContext = usePageContext()
  const { playerId, periodId } = pageContext.routeParams

  return <div>Player: {playerId}, period: {periodId}</div>
}
