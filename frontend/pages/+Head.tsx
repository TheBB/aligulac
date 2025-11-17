// https://vike.dev/Head

import { ColorSchemeScript } from "@mantine/core"
import logoUrl from "../assets/logo.svg"

export default function HeadDefault() {
  return (
    <>
      <link rel="icon" href={logoUrl} />
      <ColorSchemeScript defaultColorScheme="auto" />
    </>
  )
}
