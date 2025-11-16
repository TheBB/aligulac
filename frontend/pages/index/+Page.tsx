import { useState } from "react";
import { Counter } from "./Counter.js";
import { useSuspenseQuery } from "@tanstack/react-query";

export default function Page() {
  const isServer = typeof window === "undefined"
  const apiBase = isServer ? "http://localhost:8000" : ""
  const [playerId, setPlayerId] = useState(1)

  const result = useSuspenseQuery({
    queryKey: ['player', playerId],
    queryFn: () =>
      fetch(`${apiBase}/api/web/player?player_id=${playerId}`)
      .then(res => res.json())
  })

  return (
    <>
      <h1>My Vike app</h1>
      <p>This page is:</p>
      <ul>
        <li>Rendered to HTML.</li>
        <li>
          Interactive. <Counter />
        </li>
        <li>{JSON.stringify(result)}</li>
        <li>{JSON.stringify(isServer)}</li>
        <li>Player {playerId} <button onClick={() => setPlayerId(p => p + 1)}>Inc</button></li>
      </ul>
    </>
  );
}
