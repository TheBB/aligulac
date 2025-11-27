import { ActionIcon, Group, Pagination, Title } from "@mantine/core"
import { IconArrowLeft, IconArrowRight } from "@tabler/icons-react"
import { startTransition, useState } from "react"
import { usePageContext } from "vike-react/usePageContext"
import { useRatingList } from "../../../components/api"
import RatingList from "../../../components/RatingList"
import { periodUrl, renderDate } from "../../../components/util"

const PER_PAGE = 40

interface ControllerProps {
  nPages: number
  page: number
  setPage: (page: number) => void
  lastPeriod: number
  firstPeriod: number
  currentPeriod: number
}

const Controller: React.FC<ControllerProps> = ({
  setPage,
  page,
  nPages,
  currentPeriod,
  firstPeriod,
  lastPeriod,
}) => {
  return (
    <Group justify="space-between" mt="md" mb="md">
      <ActionIcon
        size="lg"
        component="a"
        href={periodUrl(currentPeriod + 1)}
        disabled={currentPeriod === firstPeriod}
      >
        <IconArrowLeft />
      </ActionIcon>
      <Pagination total={nPages} value={page + 1} onChange={setPage} />
      <ActionIcon
        size="lg"
        component="a"
        href={periodUrl(currentPeriod + 1)}
        disabled={currentPeriod === lastPeriod}
      >
        <IconArrowRight />
      </ActionIcon>
    </Group>
  )
}

const Page = () => {
  const pageContext = usePageContext()
  const { periodId } = pageContext.routeParams as { periodId: "latest" | number }

  const [page, setPage] = useState(0)
  const { data } = useRatingList(periodId, { limit: PER_PAGE, offset: page * PER_PAGE })

  const nPages = Math.ceil(data.count / PER_PAGE)

  const handleSetPage = (page: number) => {
    startTransition(() => {
      setPage(page - 1)
    })
  }

  const Ctrl = () => (
    <Controller
      page={page}
      setPage={handleSetPage}
      nPages={nPages}
      lastPeriod={data.last_period_id}
      firstPeriod={data.first_period_id}
      currentPeriod={data.period_id}
    />
  )

  return (
    <>
      <Title order={1}>Rating list - {renderDate(data.period_end)}</Title>
      <Ctrl />
      <RatingList data={data.ratings} />
      <Ctrl />
    </>
  )
}

export default Page
