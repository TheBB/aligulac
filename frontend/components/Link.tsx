import { NavLink, ThemeIcon } from "@mantine/core"
import type { FC, ReactNode } from "react"
import { usePageContext } from "vike-react/usePageContext"

interface LinkProps {
  href: string
  label: string
  className?: string
  icon?: FC
  leftSection?: ReactNode
}

const Link: FC<LinkProps> = ({ href, label, className, icon: Icon }) => {
  const pageContext = usePageContext()
  const { urlPathname } = pageContext
  const isActive =
    href === "/" ? urlPathname === href : urlPathname.startsWith(href)
  return (
    <NavLink
      href={href}
      label={label}
      active={isActive}
      className={className}
      leftSection={
        Icon && (
          <ThemeIcon variant="light" size={30}>
            <Icon />
          </ThemeIcon>
        )
      }
      variant="subtle"
    />
  )
}

export default Link
