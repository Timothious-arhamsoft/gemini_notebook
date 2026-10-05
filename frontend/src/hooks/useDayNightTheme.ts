import { useState, useEffect } from 'react'

export function useDayNightTheme() {
  // Helper to determine if local system time is between 6 AM and 6 PM
  const checkIsDay = () => {
    const hour = new Date().getHours()
    return hour >= 6 && hour < 18
  }

  const [isDay, setIsDay] = useState(checkIsDay)

  // Live timer interval to sync theme with local time
  useEffect(() => {
    const updateTheme = () => {
      setIsDay(checkIsDay())
    }

    updateTheme()
    const timer = setInterval(updateTheme, 30000) // check every 30s

    return () => clearInterval(timer)
  }, [])

  const toggleTheme = () => setIsDay(prev => !prev)

  return { isDay, setIsDay, toggleTheme }
}
