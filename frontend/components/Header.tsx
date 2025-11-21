import { Anchor, Group, TextInput } from "@mantine/core"
import { IconSearch } from "@tabler/icons-react"

import ThemeSelector from "./ThemeSelector"
import MainMenu from "./Menu"

import logoUrl from "../assets/caligula-transparent-tight.png"

import classes from "./Header.module.css"


interface HeaderProps {
  openLogin: () => void,
}

const Header: React.FC<HeaderProps> = ({ openLogin }) => {
  return (
    <Group justify="space-between" align="center" h="100%" px="md" className={classes.header}>
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
  )
}

export default Header
