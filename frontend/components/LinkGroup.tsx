import { Box, Collapse, Group, ThemeIcon, UnstyledButton } from "@mantine/core"
import { IconChevronRight } from "@tabler/icons-react"
import { useState } from "react"
import { usePageContext } from "vike-react/usePageContext"
import { isLinkActive, Link } from "./Link"
import classes from "./LinkGroup.module.css"

interface LinksGroupProps {
  icon: React.FC<{ size?: number }>
  label: string
  initiallyOpened?: boolean
  links?: {
    label: string
    link: string
    icon?: React.FC
    exact?: boolean
    params?: { [k: string]: string }
  }[]
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
  const pageContext = usePageContext()
  const [opened, setOpened] = useState(
    initiallyOpened ||
      (hasLinks &&
        links.some(({ link, exact }) =>
          isLinkActive(pageContext, link, exact),
        )),
  )
  const items = (hasLinks ? links : []).map(
    ({ link, label, icon, exact, params }) => (
      <Link
        key={link}
        href={link}
        label={label}
        className={classes.link}
        icon={icon}
        exact={exact}
        params={params}
      />
    ),
  )

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
