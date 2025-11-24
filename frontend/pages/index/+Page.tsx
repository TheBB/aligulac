import { Text, Title } from "@mantine/core"
import { IconArrowRight } from "@tabler/icons-react"
import { useRecentBlog, useTopTen } from "../../components/api.js"
import BlogPosts from "../../components/BlogPosts.js"
import RatingList from "../../components/RatingList.js"
import TextAnchor from "../../components/TextAnchor.js"
import { periodUrl, renderDate } from "../../components/util.js"

export default function Page() {
  const { data: topTen } = useTopTen()
  const { data: blog } = useRecentBlog()

  return (
    <>
      <Title order={1}>Current top 10</Title>
      <RatingList data={topTen.ratings} />
      <Text c="dimmed" ta="right" mt="sm" mb="lg">
        This is a preview of the next rating list, which will be finalized on {renderDate(topTen.period_end)}.{" "}
        <TextAnchor href={periodUrl(topTen.period_id)}>Full list</TextAnchor>.
      </Text>

      <BlogPosts posts={blog.posts} />
      <Text ta="right">
        <TextAnchor href="/about/blog">
          More news <IconArrowRight size="1em" />
        </TextAnchor>
      </Text>
    </>
  )
}
