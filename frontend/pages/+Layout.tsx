import "@mantine/core/styles.css"
import type { MantineThemeOverride } from "@mantine/core"
import { ActionIcon, AppShell, createTheme, MantineProvider, useComputedColorScheme, useMantineColorScheme } from "@mantine/core"
import { Navbar } from "../components/Navbar"

import "./root.css"
import { IconMoon, IconSun } from "@tabler/icons-react"


const theme: MantineThemeOverride = createTheme({
  primaryColor: "violet",
})

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <AppShell
        navbar={{
          width: 300,
          breakpoint: "sm",
        }}
        padding="md"
      >
        <AppShell.Navbar>
          <Navbar />
        </AppShell.Navbar>
        <AppShell.Main> {children} </AppShell.Main>
      </AppShell>
    </MantineProvider>
  )
}
