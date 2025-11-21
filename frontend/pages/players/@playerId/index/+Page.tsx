import { usePageContext } from "vike-react/usePageContext";

export default function Page() {
  const pageContext = usePageContext()
  const { playerId } = pageContext.routeParams

  return <div>Player: {playerId}</div>
}
