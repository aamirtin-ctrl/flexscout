import { Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Map, List, Kanban, BarChart3, Bell, Settings } from 'lucide-react'
import CommandCenter from './pages/CommandCenter'
import MapView from './pages/MapView'
import DealList from './pages/DealList'
import DealDetail from './pages/DealDetail'
import Pipeline from './pages/Pipeline'
import Market from './pages/Market'
import Alerts from './pages/Alerts'
import SettingsPage from './pages/Settings'
import DealSlideOut from './components/DealSlideOut'
import { useFilterStore } from './store/filters'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Command Center' },
  { to: '/map', icon: Map, label: 'Map' },
  { to: '/deals', icon: List, label: 'Deals' },
  { to: '/pipeline', icon: Kanban, label: 'Pipeline' },
  { to: '/market', icon: BarChart3, label: 'Market' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function App() {
  const selectedDealId = useFilterStore((s) => s.selectedDealId)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar nav */}
      <nav className="w-14 bg-surface border-r border-border flex flex-col items-center py-4 gap-1 shrink-0">
        <div className="text-primary font-bold text-lg mb-4">FS</div>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `w-10 h-10 flex items-center justify-center rounded-lg transition-colors ${
                isActive ? 'bg-primary/20 text-primary' : 'text-muted hover:text-text hover:bg-white/5'
              }`
            }
            title={label}
          >
            <Icon size={20} />
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/map" element={<MapView />} />
          <Route path="/deals" element={<DealList />} />
          <Route path="/deals/:id" element={<DealDetail />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/market" element={<Market />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>

      {/* Slide-out deal detail */}
      {selectedDealId && <DealSlideOut dealId={selectedDealId} />}
    </div>
  )
}
