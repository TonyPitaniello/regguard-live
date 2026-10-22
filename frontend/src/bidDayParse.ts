export type BidDayLine = {
  raw: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  error: string;
};

const LINE =
  /^(.+?),\s*([^,]+?),\s*([A-Za-z]{2})\s+(\d{5})(?:-\d{4})?\s*$/;

/** One address per line: street, city, ST ZIP. Cap is the paste limit, not the run limit. */
export function parseBidDayLines(text: string, cap = 12): BidDayLine[] {
  const lines = text
    .split(/\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));
  return lines.slice(0, cap).map((raw) => {
    const match = raw.match(LINE);
    if (!match) {
      return {
        raw,
        address: '',
        city: '',
        state: '',
        zip: '',
        error: 'Use street, city, ST ZIP',
      };
    }
    return {
      raw,
      address: match[1].trim(),
      city: match[2].trim(),
      state: match[3].toUpperCase(),
      zip: match[4],
      error: '',
    };
  });
}
