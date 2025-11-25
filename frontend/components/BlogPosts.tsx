import { Group, Text, Title } from "@mantine/core"
import Markdown from "react-markdown"
import classes from "./BlogPosts.module.css"
import type { components } from "./models"
import { renderDate } from "./util"

type BlogPost = components["schemas"]["BlogPost"]

interface BlogPostProps {
  post: BlogPost
}

const BlogPost: React.FC<BlogPostProps> = ({ post }) => {
  return (
    <>
      <Group justify="space-between" align="end" className={classes.title} mt="md">
        <Title order={2} style={{ display: "inline" }}>
          {post.title}
        </Title>
        <Text c="dimmed" size="sm" component="span">
          {post.author} on {renderDate(post.date)}
        </Text>
      </Group>
      <Text mb="xl">
        <Markdown>{post.text}</Markdown>
      </Text>
    </>
  )
}

interface BlogPostsProps {
  posts: BlogPost[]
}

const BlogPosts: React.FC<BlogPostsProps> = ({ posts }) => {
  return (
    <>
      {posts.map((post, i) => (
        <BlogPost key={i} post={post} />
      ))}
    </>
  )
}

export default BlogPosts
