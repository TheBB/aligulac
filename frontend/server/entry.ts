import { apply, serve } from "@photonjs/hono"
import { Hono } from "hono"

const port = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000

export default startServer()

function startServer() {
  const app = new Hono()

  apply(app)

  return serve(app, {
    port,
  })
}
