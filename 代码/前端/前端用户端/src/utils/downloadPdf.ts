/** 从 Content-Disposition 解析文件名 */
export function parseFilenameFromDisposition(header: string | undefined, fallback: string): string {
  if (!header) return fallback
  const quoted = header.match(/filename="(.+)"/)
  if (quoted) return quoted[1]
  const utf8 = header.match(/filename\*=UTF-8''(.+)/i)
  if (utf8) {
    try {
      return decodeURIComponent(utf8[1])
    } catch {
      return utf8[1]
    }
  }
  return fallback
}

export function savePdfBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export function savePdfFromAxiosResponse(
  response: { data: unknown; headers?: Record<string, string> },
  defaultFilename: string,
) {
  const raw = response.data
  const blob =
    raw instanceof Blob ? raw : new Blob([raw as BlobPart], { type: 'application/pdf' })
  const filename = parseFilenameFromDisposition(
    response.headers?.['content-disposition'],
    defaultFilename,
  )
  savePdfBlob(blob, filename)
}
