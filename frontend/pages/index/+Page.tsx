import { Box, Center, NumberFormatter, ThemeIcon } from "@mantine/core"
import { IconCaretDownFilled, IconCaretUpFilled } from "@tabler/icons-react"
import { DataTable } from "mantine-datatable"
import type React from "react"

import { useTopTen } from "../../components/Api.js"
import CountryFlag from "../../components/CountryFlag.js"
import RaceIcon from "../../components/RaceIcon.js"

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

interface PositionArrowsProps {
  current: number | null
  previous: number | null
}

const PositionArrows: React.FC<PositionArrowsProps> = ({ current, previous }) => {
  console.log(current, previous)
  if (current === null && previous === null) {
    return null
  }

  if (previous === null) {
    return <Arrows magnitude={1} />
  }

  if (current === null) {
    return <Arrows magnitude={-1} />
  }

  if (current === previous) {
    return null
  }

  return <Arrows magnitude={current > previous ? 1 : -1} />
}

export default function Page() {
  const { data } = useTopTen()

  return (
    <DataTable
      records={data.ratings}
      idAccessor="player.id"
      verticalAlign="center"
      columns={[
        {
          accessor: "current.position",
          title: "#",
          width: "3em",
          textAlign: "right",
        },
        {
          accessor: "index",
          title: "",
          width: "2em",
          textAlign: "center",
          render: (entry) => (
            <Center ml="-2em">
              <PositionArrows current={entry.current.position} previous={entry.previous.position} />
            </Center>
          ),
        },
        {
          accessor: "player.country",
          title: "",
          textAlign: "center",
          width: "2em",
          render: (entry) => (
            <Center>
              <CountryFlag code={entry.player.country} />
            </Center>
          ),
        },
        {
          accessor: "player.race",
          title: "",
          textAlign: "center",
          width: "2em",
          render: (entry) => (
            <Center>
              <RaceIcon race={entry.player.race} />
            </Center>
          ),
        },
        {
          accessor: "player.tag",
          title: "Name",
        },
        {
          accessor: "current.rating",
          title: "Rating",
          textAlign: "right",
          width: "6em",
          render: (entry) => <Rating value={entry.current.rating} />,
        },
        {
          accessor: "current.rating_vp",
          title: "vP",
          textAlign: "right",
          width: "6em",
          render: (entry) => <Rating value={entry.current.rating + entry.current.rating_vp} />,
        },
        {
          accessor: "current.rating_vt",
          title: "vT",
          textAlign: "right",
          width: "6em",
          render: (entry) => <Rating value={entry.current.rating + entry.current.rating_vt} />,
        },
        {
          accessor: "current.rating_vz",
          title: "vZ",
          textAlign: "right",
          width: "6em",
          render: (entry) => <Rating value={entry.current.rating + entry.current.rating_vz} />,
        },
        // {
        //   accessor: "1.current.vp",
        //   render: (entry) => <Rating value={entry.current.rating + entry.current.vp} />,
        // },
        // {
        //   accessor: "1.current.vt",
        //   render: (entry) => <Rating value={entry.current.rating + entry.current.vt} />,
        // },
        // {
        //   accessor: "1.current.vz",
        //   render: (entry) => <Rating value={entry.current.rating + entry.current.vz} />,
        // },
        // {
        //   accessor: "1.current.vz.diff",
        //   render: (_entry) => <Arrows magnitude={-3} />,
        // },
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
