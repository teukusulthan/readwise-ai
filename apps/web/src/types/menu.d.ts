export interface IPrivilege {
  label: string
  value: string
  description: string
  type?: string
}

export interface IMenuAdditional {
  container: 'boxed' | 'full' | 'fluid'
  iconType: 'phosphor' | 'svg-code'
  iconStyle: string
  iconStyleActive: string
  mainPage: boolean
  redirectToEnabled: boolean
  redirectTo: string
}

export interface IMenu {
  id: string
  idParent: string
  display: string
  name: string
  path: string
  show: boolean
  search: boolean
  enabled: boolean
  group: 'data' | 'system' | 'organization' | 'workspace' | 'application'
  type: 'menu'
  icon: string
  seo: { title: string; description: string }
  privileges: IPrivilege[] | null
  tactical?: boolean
  additional?: IMenuAdditional
}
