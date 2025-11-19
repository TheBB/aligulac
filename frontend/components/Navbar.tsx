import {
  ActionIcon,
  Anchor,
  Button,
  Group,
  Menu,
  PasswordInput,
  Popover,
  ScrollArea,
  TextInput,
  Title,
  useComputedColorScheme,
  useMantineColorScheme,
} from "@mantine/core"
import { useForm } from "@mantine/form"
import { useDisclosure } from "@mantine/hooks"
import {
  IconCategory2,
  IconChartLine,
  IconHome,
  IconInfoCircle,
  IconLogin,
  IconMicroscope,
  IconMoon,
  IconScoreboard,
  IconSend,
  IconSun,
  IconTrophy,
  IconUserFilled,
  IconUsersGroup,
} from "@tabler/icons-react"
import logoUrl from "../assets/caligula-transparent-tight.png"
import { useUser } from "./Api"
import { LinksGroup } from "./LinkGroup"
import classes from "./Navbar.module.css"

const ThemeSelector = () => {
  const { setColorScheme } = useMantineColorScheme()
  const computedColorScheme = useComputedColorScheme("light", {
    getInitialValueInEffect: true,
  })

  return (
    <ActionIcon
      onClick={() => setColorScheme(computedColorScheme === "light" ? "dark" : "light")}
      variant="default"
      size="xl"
      radius="md"
    >
      <IconSun size={22} className={classes.light} />
      <IconMoon size={22} className={classes.dark} />
    </ActionIcon>
  )
}

const UserMenu = ({ username, onLogout }: { username: string; onLogout: () => Promise<void> }) => {
  return (
    <Menu>
      <Menu.Target>
        <Button variant="default" leftSection={<IconUserFilled />}>
          {username}
        </Button>
      </Menu.Target>

      <Menu.Dropdown>
        <Menu.Item onClick={onLogout}>Log out</Menu.Item>
      </Menu.Dropdown>
    </Menu>
  )
}

const LoginButton = ({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) => {
  const [opened, { close, toggle }] = useDisclosure(false)

  const onSubmit = (username: string, password: string) => {
    close()
    onLogin(username, password)
  }

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
    <Popover withArrow trapFocus opened={opened} onDismiss={close}>
      <Popover.Target>
        <Button variant="default" onClick={toggle} leftSection={<IconLogin />}>
          Log in
        </Button>
      </Popover.Target>

      <Popover.Dropdown>
        <form onSubmit={form.onSubmit((values) => onSubmit(values.username, values.password))}>
          <Group align="end">
            <TextInput
              label="Username"
              w="15em"
              key={form.key("username")}
              {...form.getInputProps("username")}
            />
            <PasswordInput
              label="Password"
              w="15em"
              key={form.key("password")}
              {...form.getInputProps("password")}
            />
            <Button type="submit">Log in</Button>
          </Group>
        </form>
      </Popover.Dropdown>
    </Popover>
  )
}

const menu = [
  {
    label: "Home",
    icon: IconHome,
    link: "/",
  },
  {
    label: "Ratings",
    icon: IconChartLine,
    links: [
      { label: "Current", link: "/periods/latest" },
      { label: "History", link: "/periods", exact: true },
      { label: "Earnings", link: "/earnings" },
    ],
  },
  {
    label: "Teams",
    icon: IconUsersGroup,
    links: [
      { label: "Teams", link: "/teams" },
      { label: "Transfers", link: "/transfers" },
    ],
  },
  {
    label: "Records",
    icon: IconTrophy,
    links: [
      { label: "History", link: "/records/history" },
      { label: "Hall of Fame", link: "/records/hof" },
      {
        label: "All races",
        link: "/records/race?race=all",
        params: { race: "all" },
      },
      { label: "Protoss", link: "/records/race?race=P", params: { race: "P" } },
      { label: "Terran", link: "/records/race?race=T", params: { race: "T" } },
      { label: "Zerg", link: "/records/race?race=Z", params: { race: "Z" } },
    ],
  },
  {
    label: "Results",
    icon: IconScoreboard,
    links: [
      { label: "By date", link: "/results", exact: true },
      { label: "By event", link: "/results/events" },
      { label: "Search", link: "/results/search" },
    ],
  },
  {
    label: "Predict",
    icon: IconMicroscope,
    link: "/inference",
  },
  {
    label: "Misc",
    icon: IconCategory2,
    links: [
      { label: "Balance report", link: "/misc/balance" },
      { label: "Days since...", link: "/misc/days" },
      { label: "Compare", link: "/misc/compare" },
    ],
  },
  {
    label: "About",
    icon: IconInfoCircle,
    links: [
      { label: "FAQ", link: "/about/faq" },
      { label: "Blog", link: "/about/blog" },
      { label: "Database", link: "/about/db" },
      { label: "API", link: "/about/api" },
    ],
  },
  {
    label: "Submit",
    icon: IconSend,
    links: [
      { label: "Matches", link: "/add", exact: true },
      { label: "Review", link: "/add/review" },
      { label: "Events", link: "/add/events" },
      { label: "Open events", link: "/add/open_events" },
      { label: "Player info", link: "/add/player_info" },
      { label: "Misc", link: "/add/misc" },
    ],
  },
]

export function Navbar() {
  const links = menu.map((item) => <LinksGroup {...item} key={item.label} />)
  const { username, login, logout } = useUser()

  return (
    <nav className={classes.navbar}>
      <div className={classes.header}>
        <Anchor href="/" underline="never" c="inherit">
          <Group justify="flex-start">
            <img src={logoUrl} style={{ width: 40 }} alt="Logo" />
            <Title order={2} style={{ fontFamily: "Marcellus SC", letterSpacing: "0.2em" }}>
              ALIGULAC
            </Title>
          </Group>
        </Anchor>
      </div>

      <ScrollArea className={classes.links}>
        <div className={classes.linksInner}>{links}</div>
      </ScrollArea>

      <div className={classes.footer}>
        <Group justify="space-between">
          {username ? (
            <UserMenu username={username} onLogout={logout}></UserMenu>
          ) : (
            <LoginButton onLogin={login} />
          )}
          <ThemeSelector />
        </Group>
      </div>
    </nav>
  )
}
