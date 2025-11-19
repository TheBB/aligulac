import { Box, Collapse, Group, UnstyledButton } from "@mantine/core"
import { IconChevronRight } from "@tabler/icons-react"
import { type FC, useState } from "react"
import Link from "./Link"

import classes from "./LinkGroup.module.css"

interface LinkGroupProps {
  icon: FC
  label: string
  initiallyOpened?: boolean
  links?: { label: string; link: string; icon?: FC }[]
}

const LinkGroup: FC<LinkGroupProps> = ({
  icon: Icon,
  label,
  initiallyOpened,
  links,
}) => {
  const [opened, setOpened] = useState(initiallyOpened ?? false)
  const items = (links ?? []).map(({ label, link, icon: Icon }) => (
    <Group className={classes.link} key={link}>
      <Link href={link} label={label} icon={Icon} indented={true} />
    </Group>
  ))

  return (
    <>
      <UnstyledButton
        onClick={() => setOpened((o) => !o)}
        className={classes.control}
      >
        <Group justify="space-between">
          <Group>
            <Icon size={18} />
            <Box>{label}</Box>
          </Group>
          <IconChevronRight
            style={{ transform: opened ? "rotate(90deg)" : "none" }}
            className={classes.chevron}
          />
        </Group>
      </UnstyledButton>
      <Collapse in={opened}>{items}</Collapse>
    </>
  )
}

export default LinkGroup
