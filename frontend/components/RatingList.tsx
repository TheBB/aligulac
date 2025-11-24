import { ActionIcon, NumberFormatter } from "@mantine/core"
import { IconCaretRightFilled } from "@tabler/icons-react"
import { DataTable, type DataTableColumn } from "mantine-datatable"
import { PositionArrows, RatingArrows } from "./Arrows"
import CountryFlag from "./CountryFlag"
import type { components } from "./models"
import RaceIcon from "./RaceIcon"
import classes from "./RatingList.module.css"
import TextAnchor from "./TextAnchor"
import { playerPeriodUrl, playerUrl } from "./util"


type ListedRatingEntry = components["schemas"]["ListedRatingEntry"]

const Rating: React.FC<{ value: number }> = ({ value }) => {
  return <NumberFormatter value={(value + 1) * 1000} decimalScale={0} />
}

const ARROWS_STYLE: Partial<DataTableColumn<ListedRatingEntry>> = {
  title: "",
  width: "20px",
  cellsClassName: classes.arrows,
  textAlign: "left",
}

const RATING_STYLE: Partial<DataTableColumn<ListedRatingEntry>> = {
  width: "6em",
  textAlign: "right",
}

interface RatingListProps {
  data: ListedRatingEntry[]
}

const RatingList: React.FC<RatingListProps> = ({ data }) => {
  return (
    <DataTable
      records={data}
      idAccessor="player.id"
      verticalAlign="center"
      striped
      highlightOnHover
      columns={[
        {
          accessor: "current.position",
          title: "#",
          width: "50px",
          textAlign: "right",
        },
        {
          ...ARROWS_STYLE,
          accessor: "current.position.diff",
          render: (entry) => (
            <PositionArrows current={entry.current.position} previous={entry.previous?.position} />
          ),
        },
        {
          accessor: "player.country",
          title: "",
          textAlign: "right",
          width: "50px",
          render: (entry) => <CountryFlag code={entry.player.country} />,
        },
        {
          accessor: "player.race",
          title: "",
          textAlign: "center",
          width: "30px",
          cellsClassName: classes.race,
          render: (entry) => <RaceIcon race={entry.player.race} />,
        },
        {
          accessor: "player.tag",
          title: "Name",
          render: (entry) => <TextAnchor href={playerUrl(entry.player)}>{entry.player.tag}</TextAnchor>,
        },
        {
          ...RATING_STYLE,
          accessor: "current.rating",
          title: "Rating",
          render: (entry) => <Rating value={entry.current.rating} />,
        },
        {
          ...ARROWS_STYLE,
          accessor: "current.rating.diff",
          render: (entry) => (
            <RatingArrows current={entry.current.rating} previous={entry.previous?.rating} />
          ),
        },
        {
          ...RATING_STYLE,
          accessor: "current.rating_vp",
          title: "vP",
          render: (entry) => <Rating value={entry.current.rating + entry.current.rating_vp} />,
        },
        {
          ...ARROWS_STYLE,
          accessor: "current.rating_vp.diff",
          render: (entry) => (
            <RatingArrows
              current={entry.current.rating + entry.current.rating_vp}
              previous={entry.previous && entry.previous.rating + entry.previous.rating_vp}
            />
          ),
        },
        {
          ...RATING_STYLE,
          accessor: "current.rating_vt",
          title: "vT",
          render: (entry) => <Rating value={entry.current.rating + entry.current.rating_vt} />,
        },
        {
          ...ARROWS_STYLE,
          accessor: "current.rating_vt.diff",
          render: (entry) => (
            <RatingArrows
              current={entry.current.rating + entry.current.rating_vt}
              previous={entry.previous && entry.previous.rating + entry.previous.rating_vt}
            />
          ),
        },
        {
          ...RATING_STYLE,
          accessor: "current.rating_vz",
          title: "vZ",
          render: (entry) => <Rating value={entry.current.rating + entry.current.rating_vz} />,
        },
        {
          ...ARROWS_STYLE,
          accessor: "current.rating_vz.diff",
          render: (entry) => (
            <RatingArrows
              current={entry.current.rating + entry.current.rating_vz}
              previous={entry.previous && entry.previous.rating + entry.previous.rating_vz}
            />
          ),
        },
        {
          accessor: "current.detail",
          title: "",
          width: "40px",
          cellsClassName: classes.detail,
          render: (entry) =>
            entry.current.decay === 0 ? (
              <ActionIcon
                size="xs"
                variant="subtle"
                color="grey"
                component="a"
                href={playerPeriodUrl(entry.player, entry.current.period_id)}
              >
                <IconCaretRightFilled />
              </ActionIcon>
            ) : null,
        },
      ]}
    />
  )
}

export default RatingList
