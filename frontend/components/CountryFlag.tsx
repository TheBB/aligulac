const getCountryFlagEmoji = (countryCode: string) => {
  const codePoints = countryCode
    .toUpperCase()
    .split("")
    .map((char) => 127397 + char.charCodeAt(0))
  return String.fromCodePoint(...codePoints)
}

interface CountryFlagProps {
  code: string | null | undefined
}

const CountryFlag: React.FC<CountryFlagProps> = ({ code }) => {
  if (code === "UK") {
    code = "GB"
  }
  return code ? getCountryFlagEmoji(code) : null
}

export default CountryFlag
