import { Button, Group, Menu, ThemeIcon } from "@mantine/core"
import { IconChevronDown, IconChevronLeft, IconLogin, IconLogout, IconUserFilled } from "@tabler/icons-react"
import type React from "react"
import { usePageContext } from "vike-react/usePageContext"
import { useUser } from "./Api"
import { isLinkActive } from "./Link"

interface UserMenuSectionProps {
  onLogin: () => void
}

const UserMenuSection: React.FC<UserMenuSectionProps> = ({ onLogin }) => {
  const { username, logout } = useUser()

  return (
    <>
      <Menu.Divider />
      {username && <Menu.Item leftSection={smallIcon(IconUserFilled)}>{username}</Menu.Item>}
      {username && (
        <Menu.Item leftSection={smallIcon(IconLogout)} onClick={logout}>
          Log out
        </Menu.Item>
      )}
      {!username && (
        <Menu.Item leftSection={smallIcon(IconLogin)} onClick={onLogin}>
          Log in
        </Menu.Item>
      )}
    </>
  )
}

interface MenuItem {
  label: string
  link: string
  exact?: boolean
  params?: { [k: string]: string }
  extra?: React.FC<UserMenuSectionProps>
  icon?: React.FC
}

interface MenuGroupItem {
  label: string
  links: MenuItem[]
  extra?: React.FC<UserMenuSectionProps>
}

interface MenuSingleItem {
  label: string
  link: string
}

const menu: (MenuGroupItem | MenuSingleItem)[] = [
  {
    label: "Ratings",
    links: [
      { label: "Current", link: "/periods/latest" },
      { label: "History", link: "/periods", exact: true },
      { label: "Earnings", link: "/earnings" },
    ],
  },
  {
    label: "Teams",
    links: [
      { label: "Teams", link: "/teams" },
      { label: "Transfers", link: "/transfers" },
    ],
  },
  {
    label: "Records",
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
    links: [
      { label: "By date", link: "/results", exact: true },
      { label: "By event", link: "/results/events" },
      { label: "Search", link: "/results/search" },
    ],
  },
  {
    label: "Predict",
    link: "/inference",
  },
  {
    label: "Misc",
    links: [
      { label: "Balance report", link: "/misc/balance" },
      { label: "Days since...", link: "/misc/days" },
      { label: "Compare", link: "/misc/compare" },
    ],
  },
  {
    label: "About",
    links: [
      { label: "FAQ", link: "/about/faq" },
      { label: "Blog", link: "/about/blog" },
      { label: "Database", link: "/about/db" },
      { label: "API", link: "/about/api" },
    ],
  },
  {
    label: "Submit",
    links: [
      { label: "Matches", link: "/add", exact: true },
      { label: "Review", link: "/add/review" },
      { label: "Events", link: "/add/events" },
      { label: "Open events", link: "/add/open_events" },
      { label: "Player info", link: "/add/player_info" },
      { label: "Misc", link: "/add/misc" },
    ],
    extra: UserMenuSection,
  },
]

const smallIcon = (Icon: React.FC, ml?: number) => {
  return (
    <ThemeIcon size="xs" variant="subtle" ml={ml}>
      <Icon />
    </ThemeIcon>
  )
}

type MainMenuGroupProps = MenuGroupItem & {
  onLogin: () => void
}

const MainMenuGroup: React.FC<MainMenuGroupProps> = ({ label, links, extra: Extra, onLogin }) => {
  const pageContext = usePageContext()
  const isActive = links.some(({ link, exact, params }) => isLinkActive(pageContext, link, exact, params))

  return (
    <Menu
      offset={0}
      radius={0}
      trigger="click-hover"
      openDelay={0}
      closeDelay={0}
      transitionProps={{ duration: 0 }}
    >
      <Menu.Target>
        <Button
          h="100%"
          variant={isActive ? "light" : "subtle"}
          radius={0}
          px="xs"
          size="sm"
          rightSection={smallIcon(IconChevronDown, -3)}
        >
          {label}
        </Button>
      </Menu.Target>

      <Menu.Dropdown w="12em">
        {links.map(({ link, label, icon: Icon, exact, params }) => {
          const isActive = isLinkActive(pageContext, link, exact, params)
          return (
            <Menu.Item
              key={link}
              component="a"
              href={link}
              leftSection={
                Icon && (
                  <ThemeIcon>
                    <Icon />
                  </ThemeIcon>
                )
              }
              rightSection={isActive && smallIcon(IconChevronLeft)}
            >
              {label}
            </Menu.Item>
          )
        })}
        {Extra && <Extra onLogin={onLogin} />}
      </Menu.Dropdown>
    </Menu>
  )
}

const MainMenuSingle: React.FC<MenuSingleItem> = ({ label, link }) => {
  const pageContext = usePageContext()
  const isActive = isLinkActive(pageContext, link)

  return (
    <Button h="100%" variant={isActive ? "light" : "subtle"} radius={0} px="xs" component="a" href={link}>
      {label}
    </Button>
  )
}

type MenuGroupProps =
  | ({ onLogin: () => void } & MenuGroupItem)
  | {
      label: string
      links?: undefined
      link: string
    }

const MainMenuItem: React.FC<MenuGroupProps> = (props) => {
  if (Array.isArray(props.links)) {
    return <MainMenuGroup {...(props as MainMenuGroupProps)} />
  } else {
    return <MainMenuSingle {...(props as MenuSingleItem)} />
  }
}

interface MainMenuProps {
  onLogin: () => void
}

const MainMenu: React.FC<MainMenuProps> = ({ onLogin }) => {
  return (
    <Group align="center" h="100%" gap={0}>
      {menu.map((x, i) => (
        <MainMenuItem key={i} {...x} onLogin={onLogin} />
      ))}
    </Group>
  )
}

export default MainMenu
