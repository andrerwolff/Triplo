import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { api, type Project } from "@/lib/api"
import { AppLayout } from "@/components/AppLayout"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowRight } from "lucide-react"

export function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  const load = () => {
    api.getProjects().then((r) => {
      setProjects(r.projects)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const createProject = () => {
    if (!newName.trim()) return
    setCreateError(null)
    setCreating(true)
    api.createProject(newName.trim())
      .then((p) => {
        setNewName("")
        setDialogOpen(false)
        setProjects((prev) => [...prev, p])
        navigate(`/project/${p.id}`)
      })
      .catch((err: Error) => {
        setCreateError(err.message || "Could not create project. Is the backend running at " + (import.meta.env.VITE_API_URL ?? "http://localhost:8000") + "?")
      })
      .finally(() => setCreating(false))
  }

  return (
    <AppLayout projects={projects}>
      <div className="flex flex-1 flex-col gap-6 p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) setCreateError(null) }}>
            <DialogTrigger asChild>
              <Button>Start New Project</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Project</DialogTitle>
                <DialogDescription>
                  Enter a name for the new project.
                </DialogDescription>
              </DialogHeader>
              <form
                className="grid gap-4 py-4"
                onSubmit={(e) => {
                  e.preventDefault()
                  createProject()
                }}
              >
                <div className="grid gap-2">
                  <Label htmlFor="project-name">Project Name</Label>
                  <Input
                    id="project-name"
                    value={newName}
                    onChange={(e) => {
                      setNewName(e.target.value)
                      setCreateError(null)
                    }}
                    onKeyDown={(e) => e.key === "Enter" && createProject()}
                    placeholder="e.g. Lafayette WRF"
                  />
                </div>
                {createError && (
                  <p className="text-sm text-destructive">{createError}</p>
                )}
                <Button type="submit" disabled={!newName.trim() || creating}>
                  {creating ? "Creating…" : "Submit"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {loading ? (
            <p className="text-muted-foreground col-span-full">Loading…</p>
          ) : projects.length === 0 ? (
            <p className="text-muted-foreground col-span-full">No projects yet. Create one with the button above.</p>
          ) : (
            projects.map((project) => (
              <Card
                key={project.id}
                role="button"
                tabIndex={0}
                className="cursor-pointer transition-colors hover:bg-accent/50 py-4 px-4"
                onClick={() => navigate(`/project/${project.id}`)}
                onKeyDown={(e) => e.key === "Enter" && navigate(`/project/${project.id}`)}
              >
                <CardContent className="flex flex-col gap-2 p-0">
                  <p className="font-medium text-sm line-clamp-1">{project.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {project.reference_docs?.length ?? 0} refs ·{" "}
                    {(project.open_submittals?.length ?? 0) + (project.closed_submittals?.length ?? 0)} submittals ·{" "}
                    {project.rfis?.length ?? 0} RFIs
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-1 w-fit"
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/project/${project.id}`)
                    }}
                  >
                    Open
                    <ArrowRight className="ml-1 size-3" />
                  </Button>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </AppLayout>
  )
}
