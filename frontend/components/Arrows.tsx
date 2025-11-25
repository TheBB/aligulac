import { Box } from "@mantine/core"
import { IconCaretDownFilled, IconCaretUpFilled } from "@tabler/icons-react"

import classes from "./Arrows.module.css"

const Arrows: React.FC<{ magnitude: number }> = ({ magnitude }) => {
  if (magnitude === 0) {
    return null
  }
  const Arrow = magnitude > 0 ? IconCaretUpFilled : IconCaretDownFilled
  const className = magnitude > 0 ? "green" : "red"

  if (Math.abs(magnitude) > 2) {
    return (
      <Box pos="relative" w={16} h={26} className={classes[className]}>
        <Arrow size={16} style={{ position: "absolute", top: "calc(50% - 13px)", left: "calc(50% - 8px)" }} />
        <Arrow size={16} style={{ position: "absolute", top: "calc(50% - 8px)", left: "calc(50% - 8px)" }} />
        <Arrow size={16} style={{ position: "absolute", top: "calc(50% - 3px)", left: "calc(50% - 8px)" }} />
      </Box>
    )
  }

  if (Math.abs(magnitude) > 1) {
    return (
      <Box pos="relative" w={16} h={26} className={classes[className]}>
        <Arrow size={16} style={{ position: "absolute", top: "calc(50% - 10px)", left: "calc(50% - 8px)" }} />
        <Arrow size={16} style={{ position: "absolute", top: "calc(50% - 5px)", left: "calc(50% - 8px)" }} />
      </Box>
    )
  }

  return (
    <Box pos="relative" w={16} h={26} className={classes[className]}>
      <Arrow size={16} style={{ position: "absolute", top: "calc(50% - 7px)", left: "calc(50% - 8px)" }} />
    </Box>
  )
}

interface PositionArrowsProps {
  current?: number | null
  previous?: number | null
}

export const PositionArrows: React.FC<PositionArrowsProps> = ({ current, previous }) => {
  if (
    current == null ||
    current === undefined ||
    previous == null ||
    previous === undefined ||
    current === previous
  ) {
    return null
  }

  return <Arrows magnitude={current < previous ? 1 : -1} />
}

interface RatingArrowsProps {
  current?: number | null
  previous?: number | null
}

export const RatingArrows: React.FC<RatingArrowsProps> = ({ current, previous }) => {
  if (
    current == null ||
    current === undefined ||
    previous == null ||
    previous === undefined ||
    current === previous
  ) {
    return null
  }

  const absDiff = Math.abs(current - previous)
  const magnitude = absDiff > 0.1 ? 3 : absDiff > 0.04 ? 2 : 1
  const sign = current < previous ? -1 : 1

  return <Arrows magnitude={magnitude * sign} />
}
