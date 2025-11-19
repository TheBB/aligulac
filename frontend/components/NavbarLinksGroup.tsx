import { Box, Collapse, Group, ThemeIcon, UnstyledButton } from "@mantine/core"
import { IconCalendarStats, IconChevronRight } from "@tabler/icons-react"
import { useState } from "react"
import Link from "./Link"
import classes from "./NavbarLinksGroup.module.css"

interface LinksGroupProps {
  icon: React.FC
  label: string
  initiallyOpened?: boolean
  links?: { label: string; link: string; icon?: React.FC }[]
  link?: string
}

export function LinksGroup({
  icon: Icon,
  label,
  initiallyOpened,
  links,
  link,
}: LinksGroupProps) {
  const hasLinks = Array.isArray(links)
  const [opened, setOpened] = useState(initiallyOpened || false)
  const items = (hasLinks ? links : []).map(({ link, label, icon }) => (
    <Link
      key={link}
      href={link}
      label={label}
      className={classes.link}
      icon={icon}
    />
  ))

  return hasLinks ? (
    <>
      <UnstyledButton
        onClick={() => setOpened((o) => !o)}
        className={classes.control}
      >
        <Group justify="space-between" gap={0}>
          <Box style={{ display: "flex", alignItems: "center" }}>
            <ThemeIcon variant="light" size={30}>
              <Icon size={18} />
            </ThemeIcon>
            <Box ml="sm">{label}</Box>
          </Box>
          {hasLinks && (
            <IconChevronRight
              className={classes.chevron}
              stroke={1.5}
              size={16}
              style={{ transform: opened ? "rotate(-90deg)" : "none" }}
            />
          )}
        </Group>
      </UnstyledButton>
      {hasLinks ? <Collapse in={opened}>{items}</Collapse> : null}
    </>
  ) : (
    <Link
      href={link as string}
      label={label}
      icon={Icon}
      className={classes.barelink}
    />
  )
}

const mockdata = {
  label: "Releases",
  icon: IconCalendarStats,
  links: [
    { label: "Upcoming releases", link: "/" },
    { label: "Previous releases", link: "/" },
    { label: "Releases schedule", link: "/" },
  ],
}

export function NavbarLinksGroup() {
  return (
    <Box mih={220} p="md">
      <LinksGroup {...mockdata} />
    </Box>
  )
}
