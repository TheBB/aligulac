// https://vike.dev/data

import type { PageContextServer } from "vike/types";

export type Data = Awaited<ReturnType<typeof data>>;

export async function data(_pageContext: PageContextServer) {
  // NOTE: This +data hook is only for demonstration — it doesn't actually retrieve data from a database.
  // Go to https://vike.dev/new and select a database to scaffold an app with a persisted to-do list.
  const todoItemsInitial = [{ text: "Buy milk" }, { text: "Buy strawberries" }];
  return { todoItemsInitial };
}
