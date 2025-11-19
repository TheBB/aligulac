// https://vike.dev/onPageTransitionStart

import type { PageContextClient } from "vike/types"

export async function onPageTransitionStart(_: Partial<PageContextClient>) {
  document.body.classList.add("page-transition")
}
