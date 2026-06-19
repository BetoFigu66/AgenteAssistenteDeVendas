/** Fuso horário de exibição para operadores no Brasil. */
export const TZ_BR = 'America/Sao_Paulo'

/**
 * Interpreta datetime da API como UTC (append Z quando não há offset).
 * @param {string|null|undefined} iso
 * @returns {Date|null}
 */
export function parseApiDatetime(iso) {
  if (!iso) return null
  const hasOffset = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso)
  const normalized = hasOffset ? iso : `${iso}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

/**
 * Formata datetime UTC da API em horário de Brasília.
 * @param {string|null|undefined} iso
 * @param {Intl.DateTimeFormatOptions} [options]
 * @returns {string}
 */
export function formatDatetimeBRT(iso, options = {}) {
  const date = parseApiDatetime(iso)
  if (!date) return ''
  return date.toLocaleString('pt-BR', {
    timeZone: TZ_BR,
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  })
}

/**
 * Formata apenas hora em BRT.
 * @param {string|null|undefined} iso
 * @param {Intl.DateTimeFormatOptions} [options]
 * @returns {string}
 */
export function formatTimeBRT(iso, options = {}) {
  const date = parseApiDatetime(iso)
  if (!date) return ''
  return date.toLocaleTimeString('pt-BR', {
    timeZone: TZ_BR,
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  })
}
