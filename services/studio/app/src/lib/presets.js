const KEY = 'studio:presets'

export function loadPresets() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function savePreset(name, settings) {
  const presets = loadPresets().filter(p => p.name !== name)
  presets.push({ name, ...settings })
  presets.sort((a, b) => a.name.localeCompare(b.name))
  localStorage.setItem(KEY, JSON.stringify(presets))
  return presets
}

export function deletePreset(name) {
  const presets = loadPresets().filter(p => p.name !== name)
  localStorage.setItem(KEY, JSON.stringify(presets))
  return presets
}
