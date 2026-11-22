import { componentRegistry } from "./quartz/components/registry"
import { loadQuartzConfig, loadQuartzLayout } from "./quartz/plugins/loader/config-loader"

// 볼트 파일 이름의 번호(01, 02 …) 순서대로 정렬하기 — 화면에는 번호 없는 제목만 보여요
componentRegistry.setOptionOverrides("@quartz-community/explorer", {
  sortFn: (a: any, b: any) => {
    if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1
    return (a.slugSegment || "").localeCompare(b.slugSegment || "", undefined, {
      numeric: true,
      sensitivity: "base",
    })
  },
})
componentRegistry.setOptionOverrides("@quartz-community/folder-page", {
  sort: (f1: any, f2: any) => {
    const s1: string = f1.slug ?? ""
    const s2: string = f2.slug ?? ""
    const d1 = s1.endsWith("/index")
    const d2 = s2.endsWith("/index")
    if (d1 !== d2) return d1 ? -1 : 1
    return s1.localeCompare(s2, undefined, { numeric: true, sensitivity: "base" })
  },
})

const config = await loadQuartzConfig()
export default config
export const layout = await loadQuartzLayout()
