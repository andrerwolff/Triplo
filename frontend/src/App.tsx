import { BrowserRouter, Routes, Route } from "react-router-dom"
import { DashboardPage } from "@/pages/DashboardPage"
import { ProjectPage } from "@/pages/ProjectPage"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/project/:projectId" element={<ProjectPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
