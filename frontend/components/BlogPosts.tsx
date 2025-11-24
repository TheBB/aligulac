import { Text, Title } from "@mantine/core"
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
      <Title order={2}>{post.title}</Title>
      <Text className={classes.author} c="dimmed" size="sm">
        {post.author} on {renderDate(post.date)}
      </Text>
      <Text className={classes.text}>
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
