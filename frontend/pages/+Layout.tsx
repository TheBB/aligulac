import "@mantine/core/styles.css"
import type { MantineThemeOverride } from "@mantine/core"
import { AppShell, createTheme, MantineProvider } from "@mantine/core"
import { NavbarNested } from "../components/NavbarNested"

import "./root.css"

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
          <NavbarNested />
        </AppShell.Navbar>
        <AppShell.Main> {children} </AppShell.Main>
      </AppShell>
    </MantineProvider>
  )
}
