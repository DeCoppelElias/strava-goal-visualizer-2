export type Theme = 'dark' | 'light'

export function getTheme(): Theme {
  return (localStorage.getItem('theme') as Theme) ?? 'dark'
}

export function setTheme(t: Theme) {
  localStorage.setItem('theme', t)
  document.documentElement.setAttribute('data-theme', t)
}
