import { useEffect, useState } from 'react'

function Nav({ active, setActive }: { active: string, setActive: (s: string) => void }) {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'files', label: 'Files' },
    { id: 'reddit', label: 'Reddit' },
    { id: 'login', label: 'Login' },
    { id: 'keys', label: 'Keys' },
    { id: 'api', label: 'API' },
    { id: 'privacy', label: 'Privacy' },
  ]
  return (
    <nav className="flex gap-2 p-3 border-b border-border">
      {tabs.map(t => (
        <button key={t.id} className={`px-3 py-1 rounded-card ${active===t.id ? 'bg-card text-text-primary' : 'text-text-secondary hover:text-text-primary'}`} onClick={() => setActive(t.id)}>{t.label}</button>
      ))}
    </nav>
  )
}

function Section({ title, children }: any) {
  return (
    <section className="p-4">
      <h2 className="text-lg font-semibold mb-3">{title}</h2>
      <div className="bg-card rounded-card shadow-soft p-4 border border-border">{children}</div>
    </section>
  )
}

function Dashboard() {
  const [health, setHealth] = useState<string>('checking...')
  useEffect(() => {
    fetch('/health').then(r => r.json()).then(d => setHealth(d.status || 'ok')).catch(() => setHealth('down'))
  }, [])
  return <div>API health: <span className={health==='ok' ? 'text-lime' : 'text-magenta'}>{health}</span></div>
}

function Login() {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')
  return (
    <div className="flex flex-col gap-3 max-w-md">
      <input className="bg-panel border border-border rounded-card px-3 py-2" placeholder="username" value={username} onChange={e=>setUsername(e.target.value)} />
      <input className="bg-panel border border-border rounded-card px-3 py-2" placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
      <button className="bg-cyan text-black font-semibold px-3 py-2 rounded-card" onClick={async ()=>{
        const form = new URLSearchParams({ username, password })
        const r = await fetch('/api/v1/auth/login', { method: 'POST', body: form })
        if (r.ok) setMsg('Logged in')
        else setMsg('Failed')
      }}>Login</button>
      <div className="text-text-secondary text-sm">{msg}</div>
    </div>
  )
}

function Files() {
  const [items, setItems] = useState<any[]>([])
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [uploadZip, setUploadZip] = useState(true)
  const [zipName, setZipName] = useState('upload.zip')
  const [files, setFiles] = useState<FileList | null>(null)
  const [path, setPath] = useState<string>('/')

  const load = async (p = path) => {
    const r = await fetch(`/api/v1/files/list?path=${encodeURIComponent(p)}`)
    if (r.ok) { setItems(await r.json()); setSelected({}); setPath(p) }
  }
  useEffect(() => { load('/') }, [])

  const doUpload = async () => {
    if (!files || files.length === 0) return
    const csrfRes = await fetch('/api/v1/auth/csrf'); if (!csrfRes.ok) return; const { token } = await csrfRes.json()
    const fd = new FormData()
    if (uploadZip) {
      fd.append('zip', 'true')
      fd.append('zip_name', zipName)
    }
    if (uploadZip) {
      // send all files under 'files'
      Array.from(files).forEach(f => fd.append('files', f))
    } else {
      if (files.length === 1) fd.append('file', files[0])
      else Array.from(files).forEach(f => fd.append('files', f))
    }
    const r = await fetch(`/api/v1/files/upload?path=${encodeURIComponent(path)}`, { method: 'POST', body: fd, headers: { 'X-CSRF-Token': token } })
    if (r.ok) { setFiles(null); await load() }
  }

  const downloadZip = async () => {
    const paths = Object.keys(selected).filter(k => selected[k]).map(name => `${path.replace(/\/$/, '')}/${name}`)
    if (paths.length === 0) return
    const csrfRes = await fetch('/api/v1/auth/csrf'); if (!csrfRes.ok) return; const { token } = await csrfRes.json()
    const r = await fetch('/api/v1/files/zip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
      body: JSON.stringify({ paths, name: 'bundle.zip' })
    })
    if (!r.ok) return
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'bundle.zip'; a.click()
    URL.revokeObjectURL(url)
  }

  const up = () => {
    if (path === '/') return
    const parts = path.replace(/\/+$/, '').split('/')
    parts.pop()
    const parent = parts.join('/') || '/'
    load(parent)
  }

  const allSelected = items.length > 0 && items.every(it => selected[it.name])
  const toggleAll = (checked: boolean) => {
    const next: Record<string, boolean> = {}
    if (checked) items.forEach(it => next[it.name] = true)
    setSelected(next)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-panel rounded-card p-3 border border-border flex items-center gap-3 justify-between">
        <div className="flex items-center gap-3">
          <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={up} disabled={path==='/' }>Up</button>
          <div className="text-text-secondary text-sm">Path: <span className="text-text-primary">{path}</span></div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={allSelected} onChange={e=>toggleAll(e.target.checked)} />
            <span>Select all</span>
          </label>
        </div>
      </div>
      <div className="bg-panel rounded-card p-3 border border-border flex items-center gap-3">
        <input type="file" multiple onChange={e=>setFiles(e.target.files)} />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={uploadZip} onChange={e=>setUploadZip(e.target.checked)} />
          <span className="text-text-secondary text-sm">Zip before storing</span>
        </label>
        {uploadZip && (
          <input className="bg-card border border-border rounded-card px-2 py-1 text-sm" value={zipName} onChange={e=>setZipName(e.target.value)} />
        )}
        <button className="bg-cyan text-black font-semibold px-3 py-2 rounded-card" onClick={doUpload}>Upload</button>
      </div>
      <div className="text-sm text-text-secondary">Your uploads</div>
      <ul className="grid gap-2">
        {items.map(it => (
          <li key={it.name} className="flex justify-between items-center bg-panel px-3 py-2 rounded-card border border-border">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={!!selected[it.name]} onChange={e=>setSelected(s=>({ ...s, [it.name]: e.target.checked }))} />
              {it.type==='dir' ? (
                <button className="underline decoration-dotted" onClick={()=>load(`${path.replace(/\/$/, '')}/${it.name}`)}>📁 {it.name}</button>
              ) : (
                <span>📄 {it.name}</span>
              )}
            </label>
            <span className="text-text-muted">{it.bytes} bytes</span>
          </li>
        ))}
      </ul>
      <div>
        <button className="bg-lime text-black font-semibold px-3 py-2 rounded-card" onClick={downloadZip}>Download selected as zip</button>
      </div>
    </div>
  )
}

function Keys() {
  const [keys, setKeys] = useState<any[]>([])
  const [scopes, setScopes] = useState('files:read,files:write,reddit:read')
  const [issued, setIssued] = useState<any | null>(null)
  const load = async () => {
    const r = await fetch('/api/v1/keys')
    if (r.ok) setKeys(await r.json())
  }
  useEffect(() => { load() }, [])

  const csrf = async () => {
    const r = await fetch('/api/v1/auth/csrf'); if (!r.ok) return null; const d = await r.json(); return d.token
  }

  const issue = async () => {
    const token = await csrf(); if (!token) return
    const scopeArr = scopes.split(',').map(s=>s.trim()).filter(Boolean)
    const r = await fetch('/api/v1/keys/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
      body: JSON.stringify({ scopes: scopeArr })
    })
    if (r.ok) {
      const created = await r.json(); setIssued(created)
      await load()
    }
  }

  const revoke = async (key_id: string) => {
    const token = await csrf(); if (!token) return
    const r = await fetch('/api/v1/keys/revoke', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
      body: JSON.stringify({ key_id })
    })
    if (r.ok) await load()
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-panel rounded-card p-3 border border-border flex flex-col gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-text-secondary">Presets:</span>
          <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={()=>setScopes('files:read')}>Files Read</button>
          <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={()=>setScopes('files:read,files:write')}>Files RW</button>
          <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={()=>setScopes('reddit:read')}>Reddit Read</button>
          <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={()=>setScopes('reddit:read,reddit:write')}>Reddit RW</button>
          <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={()=>setScopes('tasks:write')}>Tasks</button>
          <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={()=>setScopes('files:read,files:write,reddit:read,reddit:write,tasks:write')}>All</button>
        </div>
        <div className="flex items-center gap-3">
          <input className="bg-card border border-border rounded-card px-2 py-1 text-sm w-full" value={scopes} onChange={e=>setScopes(e.target.value)} />
          <button className="bg-cyan text-black font-semibold px-3 py-2 rounded-card" onClick={issue}>Issue Key</button>
        </div>
        {issued && (
          <div className="bg-card rounded-card p-3 border border-border text-sm">
            <div className="mb-2 text-text-secondary">Key issued. Save it now:</div>
            <div className="flex items-center gap-2"><code className="break-all">keyId={issued.key_id}</code><button className="px-2 py-1 rounded-card border border-border" onClick={()=>navigator.clipboard.writeText(issued.key_id)}>Copy</button></div>
            <div className="flex items-center gap-2 mt-1"><code className="break-all">secret={issued.secret}</code><button className="px-2 py-1 rounded-card border border-border" onClick={()=>navigator.clipboard.writeText(issued.secret)}>Copy</button></div>
          </div>
        )}
      </div>
      <div className="text-sm text-text-secondary">Existing keys</div>
      <ul className="grid gap-2">
        {keys.map(k => (
          <li key={k.key_id} className="flex justify-between items-center bg-panel px-3 py-2 rounded-card border border-border">
            <div className="text-sm">
              <div className="font-semibold">{k.key_id}</div>
              <div className="text-text-muted">scopes: {k.scopes}</div>
            </div>
            <div className="flex items-center gap-2">
              <button className="px-2 py-1 rounded-card border border-border text-sm" onClick={()=>navigator.clipboard.writeText(k.key_id)}>Copy id</button>
              <button className="bg-magenta text-black font-semibold px-3 py-2 rounded-card" onClick={()=>revoke(k.key_id)}>Revoke</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Reddit() {
  return <div>Reddit dashboard placeholder. Profile toggle and listings to come.</div>
}

function Privacy() {
  return (
    <div className="prose prose-invert max-w-none">
      <h3>Privacy</h3>
      <p>This dashboard stores only what it needs to operate:</p>
      <ul>
        <li>Username and argon2id password hash for login</li>
        <li>Session cookies (signed) for up to 24h</li>
        <li>API keys (stored hashed), scopes, and timestamps</li>
        <li>File metadata for your uploads</li>
        <li>Encrypted Reddit tokens are provided via environment and not stored by the app</li>
      </ul>
      <p>Not stored: raw passwords, raw HMAC secrets, or third-party personal data beyond what Reddit exposes through its API.</p>
      <p>Location: on the server hosting this site. Retention: until you revoke keys, logout, unlink Reddit (by rotating env), or delete files.</p>
      <p>Your controls: revoke keys, logout all sessions, rotate Reddit app credentials, and delete uploads.</p>
    </div>
  )
}

function ApiExplorer() {
  const [routes, setRoutes] = useState<any[]>([])
  const [sel, setSel] = useState<Record<string, boolean>>({})
  const [version, setVersion] = useState('3.1.0')

  useEffect(() => {
    (async () => {
      const r = await fetch('/api/v1/ops/routes')
      if (r.ok) {
        const data = await r.json()
        setRoutes(data.routes || [])
      }
    })()
  }, [])

  const download = async () => {
    const ids = Object.entries(sel).filter(([,v]) => v).map(([k]) => k)
    const params = new URLSearchParams({ version })
    ids.forEach(id => params.append('include_operation_ids', id))
    const r = await fetch(`/api/v1/ops/openapi?${params.toString()}`, { method: 'POST' })
    if (!r.ok) return
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `openapi-${version}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const allSelected = routes.length > 0 && routes.every((r:any) => sel[r.operationId])
  return (
    <div className="flex flex-col gap-4">
      <div className="bg-panel rounded-card p-3 border border-border flex items-center gap-3">
        <label className="text-sm text-text-secondary">Version:</label>
        <select className="bg-card border border-border rounded-card px-2 py-1 text-sm" value={version} onChange={e=>setVersion(e.target.value)}>
          <option value="3.1.0">3.1.0</option>
          <option value="3.0.3">3.0.3</option>
          <option value="3.0.2">3.0.2</option>
          <option value="3.0.1">3.0.1</option>
          <option value="3.0.0">3.0.0</option>
        </select>
        <button className="ml-auto bg-cyan text-black font-semibold px-3 py-2 rounded-card" onClick={download}>Download OpenAPI JSON</button>
      </div>
      <div className="bg-panel rounded-card p-3 border border-border">
        <label className="flex items-center gap-2 mb-2 text-sm">
          <input type="checkbox" checked={allSelected} onChange={e=>{
            const next: Record<string, boolean> = {}
            if (e.target.checked) routes.forEach((r:any) => next[r.operationId] = true)
            setSel(next)
          }} />
          <span>Select all</span>
        </label>
        <div className="grid gap-2">
          {routes.map((r:any) => (
            <label key={r.operationId} className="flex items-center gap-3 bg-card rounded-card p-2 border border-border">
              <input type="checkbox" checked={!!sel[r.operationId]} onChange={e=>setSel(s=>({ ...s, [r.operationId]: e.target.checked }))} />
              <span className="text-sm text-text-secondary w-24">{(r.methods||[]).join(',')}</span>
              <code className="break-all">{r.path}</code>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('dashboard')
  return (
    <div className="min-h-screen">
      <Nav active={tab} setActive={setTab} />
      <div className="max-w-5xl mx-auto">
        {tab==='dashboard' && <Section title="Overview"><Dashboard /></Section>}
        {tab==='files' && <Section title="Files"><Files /></Section>}
        {tab==='reddit' && <Section title="Reddit"><Reddit /></Section>}
        {tab==='login' && <Section title="Login"><Login /></Section>}
        {tab==='keys' && <Section title="API Keys"><Keys /></Section>}
        {tab==='api' && <Section title="API Explorer"><ApiExplorer /></Section>}
        {tab==='privacy' && <Section title="Privacy"><Privacy /></Section>}
      </div>
    </div>
  )
}
