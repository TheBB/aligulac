import { Anchor } from "@mantine/core"
import type { PropsWithChildren } from "react"

import classes from "./TextAnchor.module.css"

interface TextAnchorProps {
  href: string
}

const TextAnchor: React.FC<PropsWithChildren<TextAnchorProps>> = ({ href, children }) => {
  return (
    <Anchor href={href} className={classes.anchor}>
      {children}
    </Anchor>
  )
}

export default TextAnchor
