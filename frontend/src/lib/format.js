export function formatMoney(value) {
  const amount = Number(value) || 0
  if (amount >= 10_000_000) {
    const crore = amount / 10_000_000
    return `₹${Number.isInteger(crore) ? crore : crore.toFixed(1)} Cr`
  }
  if (amount >= 100_000) {
    const lakh = amount / 100_000
    return `₹${Number.isInteger(lakh) ? lakh : lakh.toFixed(1)} L`
  }
  return `₹${Math.round(amount).toLocaleString('en-IN')}`
}

export function formatOdometerValue(value, decimals = 0) {
  return Number(value ?? 0).toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}
