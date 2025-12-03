import { ActionIcon, Group, Pagination, Select, type SelectProps, Title } from "@mantine/core"
import {
  IconChevronLeftPipe,
  IconChevronRightPipe,
  IconChevronsLeft,
  IconChevronsRight,
  IconWorld,
} from "@tabler/icons-react"
import { navigate } from "vike/client/router"
import { usePageContext } from "vike-react/usePageContext"
import { useRatingList } from "../../../components/api"
import CountryFlag from "../../../components/CountryFlag"
import RatingList from "../../../components/RatingList"
import { periodUrl, renderDate } from "../../../components/util"

const PER_PAGE = 40

interface Params {
  periodId: number | "latest"
  page: number
  sort?: "vp" | "vt" | "vz"
  nats?: string
}

const useParams = (): Params => {
  const pageContext = usePageContext()
  const { periodId } = pageContext.routeParams as { periodId: string }
  const { page, sort, nats } = pageContext.urlParsed.search as {
    page?: string
    sort?: "vp" | "vt" | "vz"
    nats?: string
  }

  return {
    periodId: periodId === "latest" ? "latest" : Number(periodId),
    page: page === undefined ? 1 : Number(page),
    sort,
    nats,
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

interface CountryListProps {
  nationalities: string[]
  currentNat?: string
  onSetNationality: (country?: string) => void
}

const FilterList: React.FC<CountryListProps> = ({ nationalities, currentNat, onSetNationality }) => {
  const dispNames = new Intl.DisplayNames(["en"], { type: "region" })
  const toEnglish = (cc: string) => dispNames.of(cc) ?? cc
  const countryData = nationalities
    .map((cc) => ({ label: toEnglish(cc), value: cc }))
    .toSorted(({ label: labelA }, { label: labelB }) => (labelA < labelB ? -1 : 1))

  const handleOnChange = (value: string | null) => {
    if (value === null || value === "all") {
      onSetNationality()
    } else {
      onSetNationality(value)
    }
  }

  const renderCountry: SelectProps["renderOption"] = ({ option }) => {
    return (
      <Group w="100%" justify="space-between">
        <div>{option.label}</div>
        <div>
          {option.value === "all" && <IconWorld size="1em" />}
          {option.value !== "all" && option.value !== "foreigners" && <CountryFlag code={option.value} />}
        </div>
      </Group>
    )
  }

  return (
    <form>
      <Select
        data={[
          {
            group: "",
            items: [
              { label: "All", value: "all" },
              { label: "Non-Koreans", value: "foreigners" },
            ],
          },
          { group: "Countries", items: countryData },
        ]}
        value={currentNat ?? "all"}
        onChange={handleOnChange}
        renderOption={renderCountry}
        searchable
      />
    </form>
  )
}

const Page = () => {
  const { periodId, page, sort, nats } = useParams()
  const offset = (page - 1) * PER_PAGE

  const { data } = useRatingList(periodId, { limit: PER_PAGE, offset, sort, nats })
  const nPages = Math.ceil(data.count / PER_PAGE)

  const handleSetPage = (page: number) => {
    navigate(periodUrl(periodId, page, sort, nats))
  }

  const handleSetSort = (sort?: "vp" | "vt" | "vz") => {
    navigate(periodUrl(periodId, page, sort, nats))
  }

  const handleSetNationality = (nats?: string) => {
    navigate(periodUrl(periodId, page, sort, nats))
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
      <FilterList
        nationalities={data.nationalities}
        currentNat={nats}
        onSetNationality={handleSetNationality}
      />
      <Ctrl />
      <RatingList data={data.ratings} onSetSort={handleSetSort} sort={sort} offset={offset + 1} />
      <Ctrl />
    </>
  )
}

export default Page
