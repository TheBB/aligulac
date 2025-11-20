import protossUrl from "../assets/protoss.svg"
import randomUrl from "../assets/random.svg"
import terranUrl from "../assets/terran.svg"
import zergUrl from "../assets/zerg.svg"

import classes from "./RaceIcon.module.css"

type Race = "P" | "T" | "Z" | "R"

const URL: { [K in Race]: string } = {
  P: protossUrl,
  T: terranUrl,
  Z: zergUrl,
  R: randomUrl,
}

const ALT: { [K in Race]: string } = {
  P: "Protoss",
  T: "Terran",
  Z: "Zerg",
  R: "Random",
}

interface RaceIconProps {
  race: Race
}

const RaceIcon: React.FC<RaceIconProps> = ({ race }) => {
  return <img src={URL[race]} className={classes[race]} alt={ALT[race]} />
}

export default RaceIcon
