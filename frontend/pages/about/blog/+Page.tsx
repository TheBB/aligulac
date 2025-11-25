import { Box, Button, Loader } from "@mantine/core"
import { IconReload } from "@tabler/icons-react"
import { useInfiniteBlog } from "../../../components/api"
import BlogPosts from "../../../components/BlogPosts"

const Page = () => {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteBlog()
  return (
    <>
      {data.pages.map((page, i) => <BlogPosts key={i} posts={page.posts} />)}
      {hasNextPage && (
        <Box ta="right">
          <Button
            rightSection={isFetchingNextPage ? <Loader size="sm" /> : <IconReload />}
            disabled={isFetchingNextPage}
            variant="light"
            onClick={() => fetchNextPage()}
          >
            {isFetchingNextPage ? "Loading ..." : "Load more"}
          </Button>
        </Box>
      )}
    </>
  )
}

export default Page
