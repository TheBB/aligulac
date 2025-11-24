import { Text, Title } from "@mantine/core"
import { useTopTen } from "../../components/api.js"
import RatingList from "../../components/RatingList.js"
import { periodUrl, renderDate } from "../../components/util.js"
import TextAnchor from "../../components/TextAnchor.js"

export default function Page() {
  const { data } = useTopTen()

  return (
    <>
      <Title order={1}>Current top 10</Title>
      <RatingList data={data.ratings} />
      <Text c="dimmed" ta="right" mt="sm">
        This is a preview of the next rating list, which will be finalized
        on {renderDate(data.period_end)}. <TextAnchor href={periodUrl(data.period_id)}>Full list</TextAnchor>.
      </Text>
    </>
  )
}
