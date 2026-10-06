import { useState, useEffect } from 'react'

const THEME_KEY = 'theme'

export function useDayNightTheme() {
  const getInitialIsDay = () => {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === 'day') return true
    if (saved === 'night') return false
    const hour = new Date().getHours()
    return hour >= 6 && hour < 18
  }

  const [isDay, setIsDay] = useState(getInitialIsDay)

  // Sync html[data-theme] attribute and localStorage whenever state changes
  useEffect(() => {
    const theme = isDay ? 'day' : 'night'
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(THEME_KEY, theme)
  }, [isDay])

  // Listen for storage events (e.g. across tabs or components)
  useEffect(() => {
    const handleStorageChange = () => {
      const saved = localStorage.getItem(THEME_KEY)
      if (saved === 'day') setIsDay(true)
      else if (saved === 'night') setIsDay(false)
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  const toggleTheme = () => setIsDay(prev => !prev)

  return { isDay, setIsDay, toggleTheme }
}
