import type { MantineThemeOverride } from "@mantine/core"
import {
  Anchor,
  AppShell,
  Button,
  createTheme,
  Group,
  MantineProvider,
  Modal,
  PasswordInput,
  Stack,
  TextInput,
} from "@mantine/core"
import { useForm } from "@mantine/form"
import { useDisclosure } from "@mantine/hooks"
import { Notifications } from "@mantine/notifications"
import { IconSearch } from "@tabler/icons-react"
import type React from "react"
import type { FC } from "react"
import logoUrl from "../assets/caligula-transparent-tight.png"
import { AuthProvider, useAuth } from "../components/Api"
import MainMenu from "../components/Menu"
import ThemeSelector from "../components/ThemeSelector"

import "./global.css"

const theme: MantineThemeOverride = createTheme({})

interface LoginModalProps {
  opened: boolean
  onClose: () => void
}

const LoginModal: FC<LoginModalProps> = ({ opened, onClose }) => {
  const { login } = useAuth()
  const form = useForm({
    mode: "uncontrolled",
    initialValues: {
      username: "",
      password: "",
    },
    validate: {
      username: (value) => (value.length === 0 ? "Username must be provided" : null),
      password: (value) => (value.length === 0 ? "Password must be provided" : null),
    },
  })

  return (
    <Modal opened={opened} onClose={onClose} title="Log in" trapFocus>
      <form
        onSubmit={form.onSubmit((values) => {
          onClose()
          login(values)
        })}
      >
        <Stack gap="xs">
          <TextInput
            label="Username"
            key={form.key("username")}
            {...form.getInputProps("username")}
            data-autofocus
          />
          <PasswordInput label="Password" key={form.key("password")} {...form.getInputProps("password")} />
          <Group justify="flex-end" py="md">
            <Button type="submit">Log in</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  )
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const [loginOpened, { open: openLogin, close: closeLogin }] = useDisclosure()

  return (
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <AuthProvider>
        <Notifications />
        <LoginModal opened={loginOpened} onClose={closeLogin} />

        <AppShell
          header={{
            height: 60,
          }}
          padding="md"
        >
          <AppShell.Header>
            <Group justify="space-between" align="center" h="100%" px="md">
              <Anchor href="/" underline="never" c="inherit">
                <Group align="center" h="100%">
                  <img src={logoUrl} style={{ width: 40 }} alt="Logo" />
                </Group>
              </Anchor>

              <MainMenu onLogin={openLogin} />

              <Group>
                <TextInput w="12em" rightSection={<IconSearch />} />
                <ThemeSelector />
              </Group>
            </Group>
          </AppShell.Header>
          <AppShell.Main>{children}</AppShell.Main>
        </AppShell>
      </AuthProvider>
    </MantineProvider>
  )
}
