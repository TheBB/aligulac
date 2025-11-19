import "@mantine/core/styles.css"

import type { MantineThemeOverride } from "@mantine/core"
import { AppShell, createTheme, MantineProvider } from "@mantine/core"
import { Notifications } from "@mantine/notifications"
import { Navbar } from "../components/Navbar"

import { AuthProvider } from "../components/Api"

import "@mantine/notifications/styles.css"
import "mantine-datatable/styles.layer.css"
import "./root.css"

const theme: MantineThemeOverride = createTheme({
  primaryColor: "violet",
})

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <Notifications />
      <AuthProvider>
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
          <AppShell.Main>{children}</AppShell.Main>
        </AppShell>
      </AuthProvider>
    </MantineProvider>
  )
}
