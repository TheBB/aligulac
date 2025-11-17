import { useSuspenseQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Counter } from "./Counter.js"
import { usePageContext } from "vike-react/usePageContext"

export default function Page() {
  const isBrowser = typeof window !== "undefined"
  const isDev = import.meta.env.DEV
  const context = usePageContext()

  const apiBase = isBrowser
    ? ""
    : isDev
      ? "http://localhost:8000"
      : "http://backend:8000"
  const [playerId, setPlayerId] = useState(1)

  const result = useSuspenseQuery({
    queryKey: ["player", playerId],
    queryFn: () =>
      fetch(`${apiBase}/api/web/player?player_id=${playerId}`).then((res) =>
        res.json(),
      ),
  })

  // Server-side query to protected page
  const bob = useSuspenseQuery({
    queryKey: ["protected"],
    queryFn: () => fetch(
      `${apiBase}/api/protected`,
      {headers: {"Cookie": context.headers?.cookie ?? ""}}
    ).then(res => res.json())
  })

  return (
    <>
      <h1>My Vike app</h1>
      <p>This page is:</p>
      <ul>
        {/* <li>cookies: {context.headers?.cookie}</li> */}
        <li>{JSON.stringify(bob)}</li>
        <li>Rendered to HTML.</li>
        <li>
          Interactive. <Counter />
        </li>
        <li>{JSON.stringify(result)}</li>
        <li>{JSON.stringify({ browser: isBrowser, dev: isDev })}</li>
        <li>
          Player {playerId}{" "}
          <button type="button" onClick={() => setPlayerId((p) => p + 1)}>
            Inc
          </button>
        </li>
        <li>{JSON.stringify(context.urlParsed.search)}</li>
        <li>
          <button onClick={() => {
            fetch(`${apiBase}/api/login`, {
              method: "POST",
              body: JSON.stringify({
                username: "TheBB",
                password: "<hidden>"
              })
            }).then(response => {
                if (!response.ok) { throw new Error("damn") }
                return response.json()
              })
              .then(data => alert(`success: ${JSON.stringify(data)}`))
              .catch(error => alert(`error: ${JSON.stringify(error)}`))
          }}>
            log in
          </button>
        </li>
        <li>
          <button onClick={() => {
            fetch(`${apiBase}/api/logout`, {
              method: "POST"
            }).then(response => {
                if (!response.ok) { throw new Error("damn") }
                return response.json()
              })
              .then(data => alert(`success: ${JSON.stringify(data)}`))
              .catch(error => alert(`error: ${JSON.stringify(error)}`))
          }}>
            log out
          </button>
        </li>
        <li>
          <button onClick={() => {
            fetch(`${apiBase}/api/protected`)
              .then(response => {
                if (!response.ok) { throw new Error("damn") }
                return response.json()
              })
              .then(data => alert(`success: ${JSON.stringify(data)}`))
              .catch(error => alert(`error: ${JSON.stringify(error)}`))
          }}>
            fetch protected
          </button>
        </li>
      </ul>
    </>
  )
}
