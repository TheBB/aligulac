import { notifications } from "@mantine/notifications"
import { createContext, type ReactNode, useContext, useState } from "react"
import { usePageContext } from "vike-react/usePageContext"
import type { LoginRequest, LoginResponse } from "./models"

export const computeApiBase = () => {
  const isBrowser = typeof window !== "undefined"
  const isDev = import.meta.env.DEV
  return isBrowser
    ? "/api/web"
    : isDev
      ? "http://localhost:8000/api/web"
      : "http://backend:8000/api/web"
}

const logout = async (apiBase: string): Promise<void> => {
  const response = await fetch(`${apiBase}/logout`, { method: "POST" })
  if (!response.ok) {
    throw new Error()
  }
}

const login = async (apiBase: string, request: LoginRequest): Promise<LoginResponse> => {
  const response = await fetch(`${apiBase}/login`, { method: "POST", body: JSON.stringify(request) })
  if (!response.ok) {
    throw new Error()
  }
  return (await response.json()) as LoginResponse
}

interface Api {
  username?: string
  apiBase: string
  login: (request: LoginRequest) => void
  logout: () => void
}

const ApiContext = createContext<Api>({} as Api)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const pageContext = usePageContext()
  const initialUsername = (pageContext as { username?: string }).username
  const apiBase = computeApiBase()

  const [username, setUsername] = useState<string | undefined>(initialUsername)

  const handleLogin = (data: LoginRequest) => {
    login(apiBase, data)
      .then((response) => {
        setUsername(response.username)
        notifications.show({
          title: "Success",
          message: `Logged in as ${data.username}`,
        })
      })
      .catch((_) => {
        notifications.show({
          title: "Error",
          message: "Unable to log in",
          color: "red",
        })
      })
  }

  const handleLogout = () => {
    logout(apiBase)
      .then(() => {
        setUsername(undefined)
        notifications.show({
          title: "Success",
          message: "Logged out",
        })
      })
      .catch((_) => {
        notifications.show({
          title: "Error",
          message: "Unable to log out",
          color: "red",
        })
      })
  }

  return (
    <ApiContext.Provider value={{ username, apiBase, login: handleLogin, logout: handleLogout }}>
      {children}
    </ApiContext.Provider>
  )
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
