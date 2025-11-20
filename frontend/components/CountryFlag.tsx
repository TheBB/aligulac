const getCountryFlagEmoji = (countryCode: string) => {
  const codePoints = countryCode
    .toUpperCase()
    .split("")
    .map((char) => 127397 + char.charCodeAt(0))
  return String.fromCodePoint(...codePoints)
}

interface CountryFlagProps {
  code: string | null
}

const CountryFlag: React.FC<CountryFlagProps> = ({ code }) => {
  return code ? getCountryFlagEmoji(code) : null
}

export default CountryFlag
