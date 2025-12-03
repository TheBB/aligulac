import { ActionIcon, ThemeIcon, useComputedColorScheme, useMantineColorScheme } from "@mantine/core"
import { IconMoon, IconSun } from "@tabler/icons-react"

import classes from "./ThemeSelector.module.css"

const ThemeSelector = () => {
  const { setColorScheme } = useMantineColorScheme()
  const computedColorScheme = useComputedColorScheme("light", {
    getInitialValueInEffect: true,
  })

  return (
    <ActionIcon
      onClick={() => setColorScheme(computedColorScheme === "light" ? "dark" : "light")}
      variant="default"
      size="lg"
      radius="md"
    >
      <ThemeIcon size="lg" variant="default">
        <IconSun className={classes.light} />
        <IconMoon className={classes.dark} />
      </ThemeIcon>
    </ActionIcon>
  )
}

export default ThemeSelector
