import { Group, ScrollArea, Title } from "@mantine/core"
import {
  IconCategory2,
  IconChartLine,
  IconHome,
  IconInfoCircle,
  IconMicroscope,
  IconScoreboard,
  IconSend,
  IconTrophy,
  IconUsersGroup,
} from "@tabler/icons-react"
import logoUrl from "../assets/caligula-transparent-tight.png"
import { LinksGroup } from "./LinkGroup"
import classes from "./Navbar.module.scss"

const mockdata = [
  {
    label: "Home",
    icon: IconHome,
    link: "/",
  },
  {
    label: "Ratings",
    icon: IconChartLine,
    initiallyOpened: true,
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
      { label: "All races", link: "/records/race?race=all" },
      { label: "Protoss", link: "/records/race?race=P" },
      { label: "Terran", link: "/records/race?race=T" },
      { label: "Zerg", link: "/records/race?race=Z" },
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
  const links = mockdata.map((item) => (
    <LinksGroup {...item} key={item.label} />
  ))

  return (
    <nav className={classes.navbar}>
      <div className={classes.header}>
        <Group justify="flex-start">
          <img src={logoUrl} style={{ width: 40 }} alt="Logo" />
          <Title
            order={2}
            style={{ fontFamily: "Marcellus SC", letterSpacing: "0.2em" }}
          >
            ALIGULAC
          </Title>
        </Group>
      </div>

      <ScrollArea className={classes.links}>
        <div className={classes.linksInner}>{links}</div>
      </ScrollArea>

      <div className={classes.footer}>
        <div>User button</div>
        {/* <UserButton /> */}
      </div>
    </nav>
  )
}
