import type { PropsWithChildren } from "react"

import classes from "./Body.module.css"

const Body: React.FC<PropsWithChildren<unknown>> = ({ children }) => {
  return <div className={classes.body}>{children}</div>
}

export default Body
