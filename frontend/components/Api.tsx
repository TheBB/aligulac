import { notifications } from "@mantine/notifications"
import { useSuspenseQuery } from "@tanstack/react-query"
import { createContext, type ReactNode, useContext, useEffect, useState } from "react"
import { login, logout, topTen, whoami } from "./api"
import type { LoginRequest } from "./models"

interface Auth {
  username?: string
  login: (request: LoginRequest) => void
  logout: () => void
}

const AuthContext = createContext<Auth>({} as Auth)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [username, setUsername] = useState<string | undefined>()

  useEffect(() => {
    whoami().then((response) => setUsername(response.username))
  }, [])

  const handleLogin = (data: LoginRequest) => {
    login(data)
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
    logout()
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
    <AuthContext.Provider value={{ username, login: handleLogin, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  return useContext(AuthContext)
}

export const useTopTen = () => {
  return useSuspenseQuery({
    queryKey: ["topten"],
    queryFn: () => topTen(),
  })
}
