import { notifications } from "@mantine/notifications"
import { createContext, type ReactNode, useContext, useEffect, useState } from "react"
import { login, logout, whoami } from "./api"
import type { components } from "./models"

type LoginRequest = components["schemas"]["LoginRequest"]

interface Auth {
  username?: string
  login: (request: LoginRequest) => void
  logout: () => void
}

const AuthContext = createContext<Auth>({} as Auth)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [username, setUsername] = useState<string | undefined>()

  useEffect(() => {
    ;(async () => {
      const { data } = await whoami()
      if (data !== undefined) {
        setUsername(data.username)
      }
    })()
  }, [])

  const handleLogin = async (request: LoginRequest) => {
    const { data, error } = await login(request)

    if (data !== undefined) {
      setUsername(data.username)
      notifications.show({
        title: "Success",
        message: `Logged in as ${data.username}`,
      })
    } else {
      notifications.show({
        title: "Unable to log in",
        message: error.detail,
        color: "red",
      })
    }
  }

  const handleLogout = async () => {
    await logout()
    setUsername(undefined)
    notifications.show({
      title: "Success",
      message: "Logged out",
    })
  }

  return (
    <AuthContext.Provider value={{ username, login: handleLogin, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  return useContext(AuthContext)
}
