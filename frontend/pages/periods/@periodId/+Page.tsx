import { navigate } from "vike/client/router"
import { ActionIcon, Group, Pagination, Title } from "@mantine/core"
import { IconArrowLeft, IconArrowRight, IconChevronLeftPipe, IconChevronRightPipe, IconChevronsLeft, IconChevronsRight } from "@tabler/icons-react"
import { startTransition, useState } from "react"
import { usePageContext } from "vike-react/usePageContext"
import { useRatingList } from "../../../components/api"
import RatingList from "../../../components/RatingList"
import { periodUrl, renderDate } from "../../../components/util"

const PER_PAGE = 40

interface Params {
  periodId: number | "latest"
  page: number
}

const useParams = (): Params => {
  const pageContext = usePageContext()
  const { periodId } = pageContext.routeParams as {periodId: string}
  const { page } = pageContext.urlParsed.search as {page?: string}

  return {
    periodId: periodId === "latest" ? "latest" : Number(periodId),
    page: page === undefined ? 1 : Number(page),
  }
}

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
        variant="light"
      >
        <IconChevronsLeft />
      </ActionIcon>
      <Pagination.Root total={nPages} value={page + 1} onChange={setPage}>
        <Group gap={5}>
          <Pagination.First icon={IconChevronLeftPipe} />
          <Pagination.Previous />
          <Pagination.Items />
          <Pagination.Next />
          <Pagination.Last icon={IconChevronRightPipe} />
        </Group>
      </Pagination.Root>
      <ActionIcon
        size="lg"
        component="a"
        href={periodUrl(currentPeriod + 1)}
        disabled={currentPeriod === lastPeriod}
        variant="light"
      >
        <IconChevronsRight />
      </ActionIcon>
    </Group>
  )
}

const Page = () => {
  const { periodId, page } = useParams()
  const { data } = useRatingList(periodId, { limit: PER_PAGE, offset: (page - 1) * PER_PAGE })
  const nPages = Math.ceil(data.count / PER_PAGE)

  const handleSetPage = (page: number) => {
    navigate(periodUrl(periodId, page))
  }

  const Ctrl = () => (
    <Controller
      page={page - 1}
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
