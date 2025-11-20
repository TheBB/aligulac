import { Box, NumberFormatter, ThemeIcon } from "@mantine/core"
import { IconCaretDownFilled, IconCaretUpFilled } from "@tabler/icons-react"
import { DataTable } from "mantine-datatable"
import type React from "react"
import { useTopTen } from "../../components/Api.js"

const Rating: React.FC<{ value: number }> = ({ value }) => {
  return <NumberFormatter value={(value + 1) * 1000} decimalScale={0} />
}

const Arrows: React.FC<{ magnitude: number }> = ({ magnitude }) => {
  if (magnitude === 0) {
    return null
  }
  const Arrow = magnitude > 0 ? IconCaretUpFilled : IconCaretDownFilled
  const color = magnitude > 0 ? "green" : "red"

  if (Math.abs(magnitude) > 2) {
    return (
      <Box pos="relative" w={16} h={26}>
        <ThemeIcon color={color} variant="subtle">
          <Arrow
            size={16}
            style={{ position: "absolute", top: "calc(50% - 13px)", left: "calc(50% - 8px)" }}
          />
          <Arrow
            size={16}
            style={{ position: "absolute", top: "calc(50% - 8px)", left: "calc(50% - 8px)" }}
          />
          <Arrow
            size={16}
            style={{ position: "absolute", top: "calc(50% - 3px)", left: "calc(50% - 8px)" }}
          />
        </ThemeIcon>
      </Box>
    )
  }

  if (Math.abs(magnitude) > 1) {
    return (
      <Box pos="relative" w={16} h={26}>
        <ThemeIcon color={color} variant="subtle">
          <Arrow
            size={16}
            style={{ position: "absolute", top: "calc(50% - 10px)", left: "calc(50% - 8px)" }}
          />
          <Arrow
            size={16}
            style={{ position: "absolute", top: "calc(50% - 5px)", left: "calc(50% - 8px)" }}
          />
        </ThemeIcon>
      </Box>
    )
  }

  return (
    <Box pos="relative" w={16} h={26}>
      <ThemeIcon color={color} variant="subtle">
        <Arrow size={16} style={{ position: "absolute", top: "calc(50% - 8px)", left: "calc(50% - 8px)" }} />
      </ThemeIcon>
    </Box>
  )
}

export default function Page() {
  // const isBrowser = typeof window !== "undefined"
  // const isDev = import.meta.env.DEV
  // const context = usePageContext()

  // const apiBase = isBrowser ? "" : isDev ? "http://localhost:8000" : "http://backend:8000"
  // const [playerId, setPlayerId] = useState(1)

  // const result = useSuspenseQuery({
  //   queryKey: ["player", playerId],
  //   queryFn: () => fetch(`${apiBase}/api/web/player?player_id=${playerId}`).then((res) => res.json()),
  // })

  // // Server-side query to protected page
  // const bob = useSuspenseQuery({
  //   queryKey: ["protected"],
  //   queryFn: () =>
  //     fetch(`${apiBase}/api/web/protected`, {
  //       headers: { Cookie: context.headers?.cookie ?? "" },
  //     }).then((res) => res.json()),
  // })

  const { data } = useTopTen()

  return (
    <DataTable
      records={data.ratings}
      idAccessor="player.id"
      columns={[
        {
          accessor: "player.country",
        },
        {
          accessor: "player.race",
        },
        {
          accessor: "player.tag",
        },
        {
          accessor: "current.rating",
          render: (entry) => <Rating value={entry.current.rating} />,
        },
        {
          accessor: "current.vp",
          render: (entry) => <Rating value={entry.current.rating + entry.current.vp} />,
        },
        {
          accessor: "current.vt",
          render: (entry) => <Rating value={entry.current.rating + entry.current.vt} />,
        },
        {
          accessor: "current.vz",
          render: (entry) => <Rating value={entry.current.rating + entry.current.vz} />,
        },
        {
          accessor: "current.vz.diff",
          render: (_entry) => <Arrows magnitude={-3} />,
        },
      ]}
    />
  )

  // return (
  //   <>
  //     <h1>My Vike app</h1>
  //     <p>This page is:</p>
  //     <ul>
  //       {/* <li>cookies: {context.headers?.cookie}</li> */}
  //       <li>{JSON.stringify(bob.data)}</li>
  //       <li>Rendered to HTML.</li>
  //       <li>
  //         Interactive. <Counter />
  //       </li>
  //       <li>{JSON.stringify(result.data)}</li>
  //       {/* <li>{JSON.stringify({ browser: isBrowser, dev: isDev })}</li> */}
  //       <li>
  //         Player {playerId}{" "}
  //         <button type="button" onClick={() => setPlayerId((p) => p + 1)}>
  //           Inc
  //         </button>
  //       </li>
  //       <li>{JSON.stringify(context.urlParsed.search)}</li>
  //       <li>{JSON.stringify(data)}</li>
  //     </ul>
  //   </>
  // )
}
