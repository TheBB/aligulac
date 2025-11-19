import { NavLink, ThemeIcon } from "@mantine/core"
import type { FC, ReactNode } from "react"
import { usePageContext } from "vike-react/usePageContext"

interface LinkProps {
  href: string
  label: string
  className?: string
  icon?: FC<{ size?: number }>
  leftSection?: ReactNode
  exact?: boolean
}

const Link: FC<LinkProps> = ({ href, label, className, icon: Icon, exact }) => {
  const pageContext = usePageContext()
  const { urlPathname, urlOriginal } = pageContext
  const isActive = href.includes("?")
    ? urlOriginal === href
    : href === "/" || exact
      ? urlPathname === href
      : urlPathname.startsWith(href)

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
