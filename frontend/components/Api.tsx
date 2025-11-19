import { notifications } from "@mantine/notifications"
import { createContext, type ReactNode, useContext, useState } from "react"
import { usePageContext } from "vike-react/usePageContext"

interface Api {
  username?: string
  apiBase: string
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const ApiContext = createContext<Api>({} as Api)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const pageContext = usePageContext()
  const initialUsername = (pageContext as { username?: string }).username

  const isBrowser = typeof window !== "undefined"
  const isDev = import.meta.env.DEV
  const apiBase = isBrowser ? "" : isDev ? "http://localhost:8000" : "http://backend:8000"

  const [username, setUsername] = useState<string | undefined>(initialUsername)

  const login = async (username: string, password: string) => {
    try {
      const response = await fetch(`${apiBase}/api/web/login`, {
        method: "POST",
        body: JSON.stringify({ username, password }),
      })
      if (response.status !== 201) {
        throw new Error()
      }
      const data = await response.json()
      setUsername(data.username)
      notifications.show({
        title: "Success",
        message: `Logged in as ${data.username}`,
      })
    } catch (_) {
      notifications.show({
        title: "Error",
        message: "Unable to log in",
        color: "red",
      })
    }
  }

  const logout = async () => {
    try {
      const response = await fetch(`${apiBase}/api/web/logout`, {
        method: "POST",
      })
      if (response.status !== 201) {
        throw new Error()
      }
      setUsername(undefined)
      notifications.show({
        title: "Success",
        message: "Logged out",
      })
    } catch (_) {
      notifications.show({
        title: "Error",
        message: "Unable to log out",
        color: "red",
      })
    }
  }

  return <ApiContext.Provider value={{ username, apiBase, login, logout }}>{children}</ApiContext.Provider>
}

export const useApi = () => {
  return useContext(ApiContext)
}

export const useUser = () => {
  const api = useContext(ApiContext)
  return {
    username: api.username,
    login: api.login,
    logout: api.logout,
  }
}
