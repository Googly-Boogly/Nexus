# Frontend Architecture

## Stack

- **React 18** with TypeScript 5.6 (strict mode)
- **Vite 5** — dev server + build tool
- **Tailwind CSS 3** — utility-first styling with custom design tokens
- **Recharts 2** — dashboard charts
- **Axios** — HTTP client with auto-refresh interceptor
- **react-router-dom v6** — client-side routing

## Directory Layout

```
src/
├── main.tsx             React root, mounts <App>
├── App.tsx              BrowserRouter, AuthProvider, RequireAuth wrapper, routes
├── index.css            Global styles: corner-bracket, scan-line, glow-cyan classes
├── types/
│   └── index.ts         All TypeScript interfaces (User, Task, RagSource, etc.)
├── api/
│   └── client.ts        Axios instance + all API call functions
├── mocks/
│   └── data.ts          Static mock data used in DEMO_MODE
├── contexts/
│   └── AuthContext.tsx  Auth state (user, tokens, loginDemo, isDemoMode)
├── hooks/
│   └── useTaskStream.ts WebSocket hook for task execution streaming
├── components/
│   ├── ui.tsx           Shared component library (Card, Badge, Button, Input, etc.)
│   └── Layout.tsx       Sidebar navigation, demo mode banner
└── pages/
    ├── Login.tsx        Login form + 3 demo buttons
    ├── Dashboard.tsx    Stats overview, activity chart, recent tasks
    ├── TaskRunner.tsx   Task submission form + live output terminal + RAG sources
    ├── AuditExplorer.tsx Filterable audit log table + detail panel
    ├── SecurityFeed.tsx Security events list + severity trend chart
    ├── KnowledgeBase.tsx Search / documents / path-compare tabs
    ├── Approvals.tsx    Pending approval queue + review actions
    └── UserManagement.tsx User list with inline role/clearance editing
```

## Routing

All routes except `/login` are wrapped by `RequireAuth`, which redirects unauthenticated users to `/login`.

| Path | Page | Auth required |
|---|---|---|
| `/login` | Login | No |
| `/dashboard` | Dashboard | Yes |
| `/tasks` | TaskRunner | Yes |
| `/audit` | AuditExplorer | Yes |
| `/security` | SecurityFeed | Yes |
| `/knowledge` | KnowledgeBase | Yes |
| `/approvals` | Approvals | Yes |
| `/users` | UserManagement | Yes (admin check inside page) |
| `/` and `*` | Redirect → `/dashboard` | — |

## Design System

Custom Tailwind tokens defined in `tailwind.config.js`:

| Token | Value | Usage |
|---|---|---|
| `bg-base` | `#040911` | Page background |
| `bg-card` | `#0c1524` | Card/panel backgrounds |
| `bg-card-hover` | `#111e33` | Card hover state |
| `border` | `#1a2d4a` | All borders |
| `cyan` | `#00d4ff` | Primary accent, active states |
| `green` | `#00ff88` | Success, resolved, online |
| `amber` | `#ffaa00` | Warning, pending, demo banner |
| `red` | `#ff4444` | Error, danger, failed |
| `text-primary` | `#e2e8f0` | Main text |
| `text-secondary` | `#7a9cbf` | Labels, subtitles |
| `text-muted` | `#4a6a8a` | De-emphasized text |

Fonts: `Space Mono` (monospace — used for IDs, code, labels) and `DM Sans` (sans-serif — used for body text).

Special CSS classes in `index.css`:
- `.corner-bracket` — pseudo-element cyan corner decoration on Login card
- `.scan-line` — full-width horizontal line that sweeps down the viewport (CRT aesthetic)
- `.glow-cyan` — `text-shadow` glow on headings

## Component Library (`src/components/ui.tsx`)

All shared primitives are in one file:

| Component | Props | Notes |
|---|---|---|
| `Card` | `children`, `className` | Standard card container |
| `Badge` | `children`, `variant` | 6 variants: default/success/warning/danger/info/muted |
| `StatusBadge` | `status: TaskStatus` | Maps all 8 task statuses to a Badge variant |
| `PriorityBadge` | `priority: TaskPriority` | P1=danger, P2=warning, P3=info, P4=muted |
| `Button` | `onClick`, `variant`, `size`, `disabled`, `type`, `className` | 4 variants, 3 sizes |
| `Input` | `value`, `onChange`, `placeholder`, `type`, `className` | Controlled, passes string to onChange |
| `Select` | `value`, `onChange`, `options[]`, `className` | Controlled dropdown |
| `Textarea` | `value`, `onChange`, `placeholder`, `rows`, `className` | Controlled textarea |
| `Spinner` | `size` | sm/md/lg spinning border |
| `Terminal` | `children`, `className` | Code output area with traffic-light dots |
| `SectionHeader` | `title`, `subtitle` | Page-level heading with optional subtitle |
| `EmptyState` | `message` | Centered empty state with ◻ icon |

## Auth Flow

`AuthContext` (`src/contexts/AuthContext.tsx`) exposes:
- `user: User | null` — current user
- `loading: boolean` — true during initial token check
- `isDemoMode: boolean` — true when logged in via demo button
- `login(username, password)` — calls real API, stores tokens in localStorage
- `loginDemo(role)` — sets `demo_user` in localStorage, no API call
- `logout()` — clears localStorage

On mount, `AuthContext` checks localStorage for either `access_token` (real session) or `demo_user` (demo session) and restores state accordingly.

## DEMO_MODE

When `isDemoMode` is true:
- All pages use mock data from `src/mocks/data.ts` instead of making API calls
- `TaskRunner` plays back hardcoded agent output line-by-line with `setInterval`
- `KnowledgeBase` uses `MOCK_SEARCH_RESULTS` and `MOCK_DOCUMENTS`
- `Approvals` manages state locally with `useState`
- `Layout` shows an amber banner: "DEMO MODE — using mock data"

Pages can freely branch on `isDemoMode` without worrying about breaking real API flows.

## WebSocket Streaming (`src/hooks/useTaskStream.ts`)

The `useTaskStream(taskId)` hook:
- Opens `ws(s)://{host}/api/tasks/ws/{taskId}?token={access_token}` when `taskId` is non-null
- Reconnects with exponential backoff (1s → 2s → 4s → ... → 30s max)
- Parses each message as a `TaskEvent` and appends to the `events` array
- Extracts `sources` from `rag_retrieval` events into the `ragSources` array
- Auto-closes (`shouldReconnect = false`) on `complete` or `error` events

Returns: `{ events, ragSources, connected, disconnect }`

In `TaskRunner`, the hook is only activated for real (non-demo) tasks: `useTaskStream(!isDemoMode && activeTask ? activeTask.id : null)`.

## Vite Proxy

`vite.config.ts` proxies all `/api` requests to `http://api:8000` (the backend container hostname). WebSocket upgrades for `/api/tasks/ws/` are also proxied. This avoids CORS issues in development and matches the nginx proxy config in production.
