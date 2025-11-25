import { Button } from "@mantine/core"
import { startTransition, useState } from "react"
import { usePageContext } from "vike-react/usePageContext"
import { useRatingList } from "../../../components/api"
import RatingList from "../../../components/RatingList"

const Page = () => {
  const pageContext = usePageContext()
  const { periodId } = pageContext.routeParams as { periodId: "latest" | number }

  const [offset, setOffset] = useState(0)
  const { data } = useRatingList(periodId, { offset })

  const handleNextPage = () => {
    startTransition(() => {
      if (typeof data.next_offset === "number") {
        setOffset(data.next_offset)
      }
    })
  }

  return (
    <>
      <RatingList data={data.ratings} />
      {data.next_offset != null && <Button onClick={handleNextPage}>More</Button>}
    </>
  )
}

export default Page
