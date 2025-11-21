import { useTopTen } from "../../components/Api.js"
import RatingList from "../../components/RatingList.js"

export default function Page() {
  const { data } = useTopTen()

  return <RatingList data={data.ratings} />
}
