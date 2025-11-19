import { NavLink, ThemeIcon } from "@mantine/core"
import type { FC, ReactNode } from "react"
import type { PageContext } from "vike/types"
import { usePageContext } from "vike-react/usePageContext"

export const isLinkActive = (
  pageContext: PageContext,
  href: string,
  exact?: boolean,
  params?: { [k: string]: string },
): boolean => {
  const {
    urlPathname,
    urlParsed: { search },
  } = pageContext

  const index = href.indexOf("?")
  if (index !== -1) {
    href = href.substring(0, index)
  }

  let rval =
    href === "/" || exact ? urlPathname === href : urlPathname.startsWith(href)

  if (params !== undefined) {
    Object.entries(params).forEach(([key, value]) => {
      if (search[key] !== value) {
        rval = false
      }
    })
  }

  return rval
}

interface LinkProps {
  href: string
  label: string
  className?: string
  icon?: FC<{ size?: number }>
  leftSection?: ReactNode
  exact?: boolean
  params?: { [k: string]: string }
}

export const Link: FC<LinkProps> = ({
  href,
  label,
  className,
  icon: Icon,
  exact,
  params,
}) => {
  const pageContext = usePageContext()
  const isActive = isLinkActive(pageContext, href, exact, params)

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
