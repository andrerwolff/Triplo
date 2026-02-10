import { useState, useEffect } from "react"
import { useParams, Link, useNavigate } from "react-router-dom"
import { api, type Project, type Submittal, type EvaluationReport } from "@/lib/api"
import { AppLayout } from "@/components/AppLayout"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Upload, FileCheck, AlertCircle, Pencil } from "lucide-react"

export function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [rfiOpen, setRfiOpen] = useState(false)
  const [rfiTitle, setRfiTitle] = useState("")
  const [rfiDesc, setRfiDesc] = useState("")
  const [rfiStatus, setRfiStatus] = useState("Open")
  const [refFile, setRefFile] = useState<File | null>(null)
  const [subFile, setSubFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [submittalsView, setSubmittalsView] = useState<"open" | "closed">("open")
  const [reportDialogOpen, setReportDialogOpen] = useState(false)
  const [reportSubmittalName, setReportSubmittalName] = useState("")
  const [reportData, setReportData] = useState<EvaluationReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editName, setEditName] = useState("")
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [evaluateDialogOpen, setEvaluateDialogOpen] = useState(false)
  const [evaluateSubmittal, setEvaluateSubmittal] = useState<Submittal | null>(null)
  const [evalSpecFile, setEvalSpecFile] = useState<File | null>(null)
  const [evalSubmittalFile, setEvalSubmittalFile] = useState<File | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    api.getProjects().then((r) => setProjects(r.projects))
  }, [])

  useEffect(() => {
    if (!projectId) return
    setLoading(true)
    setLoadError(null)
    api.getProject(projectId).then((p) => {
      setProject(p)
      setLoading(false)
    }).catch((err: unknown) => {
      setLoading(false)
      setLoadError(err instanceof Error ? err.message : "Failed to load project")
    })
  }, [projectId])

  const addRfi = () => {
    if (!projectId) return
    api.addRfi(projectId, { title: rfiTitle || "Untitled", description: rfiDesc, status: rfiStatus }).then((p) => {
      setProject(p)
      setRfiTitle("")
      setRfiDesc("")
      setRfiStatus("Open")
      setRfiOpen(false)
    })
  }

  const addReferenceDoc = () => {
    if (!projectId || !refFile) return
    setUploading(true)
    api.addReferenceDoc(projectId, refFile, "").then((p) => {
      setProject(p)
      setRefFile(null)
      setUploading(false)
    }).catch(() => setUploading(false))
  }

  const addSubmittal = () => {
    if (!projectId || !subFile) return
    setUploading(true)
    api.addSubmittal(projectId, subFile, "").then((p) => {
      setProject(p)
      setSubFile(null)
      setUploading(false)
    }).catch(() => setUploading(false))
  }

  const completeSubmittal = (subId: string) => {
    if (!projectId) return
    api.completeSubmittal(projectId, subId).then(setProject)
  }

  const openReport = (report: EvaluationReport, submittalName: string) => {
    setReportData(report)
    setReportSubmittalName(submittalName)
    setReportError(null)
    setReportDialogOpen(true)
  }

  const openEditDialog = () => {
    setEditName(project?.name ?? "")
    setEditError(null)
    setEditDialogOpen(true)
  }

  const saveProjectEdit = () => {
    if (!projectId || !editName.trim()) return
    setEditError(null)
    setEditSaving(true)
    api.updateProject(projectId, { name: editName.trim() })
      .then((updated) => {
        setProject(updated)
        api.getProjects().then((r) => setProjects(r.projects))
        setEditDialogOpen(false)
      })
      .catch((e: Error) => setEditError(e.message))
      .finally(() => setEditSaving(false))
  }

  const deleteProject = () => {
    if (!projectId || !confirm("Delete this project?")) return
    api.deleteProject(projectId).then(() => navigate("/"))
  }

  const openEvaluateDialog = (sub: Submittal) => {
    setEvaluateSubmittal(sub)
    setEvalSpecFile(null)
    setEvalSubmittalFile(null)
    setReportError(null)
    setEvaluateDialogOpen(true)
  }

  const submitEvaluate = () => {
    if (!projectId || !evaluateSubmittal?.id || !evalSpecFile || !evalSubmittalFile) return
    setReportLoading(true)
    setReportError(null)
    setReportSubmittalName(evaluateSubmittal.name)
    api
      .evaluateSubmittalWithPdfs(projectId, evaluateSubmittal.id, evalSpecFile, evalSubmittalFile)
      .then(({ report, project: updated }) => {
        setProject(updated)
        setReportData(report)
        setEvaluateDialogOpen(false)
        setReportDialogOpen(true)
      })
      .catch((e: Error) => setReportError(e.message))
      .finally(() => setReportLoading(false))
  }

  const reloadProject = () => {
    if (!projectId) return
    setLoading(true)
    setLoadError(null)
    api.getProject(projectId).then((p) => {
      setProject(p)
      setLoading(false)
    }).catch((err: unknown) => {
      setLoading(false)
      setLoadError(err instanceof Error ? err.message : "Failed to load project")
    })
  }

  if (loading && !project && !loadError) {
    return (
      <AppLayout projects={projects}>
        <div className="flex flex-1 items-center justify-center p-6">
          <p className="text-muted-foreground">Loading…</p>
        </div>
      </AppLayout>
    )
  }

  if (loadError && !project) {
    return (
      <AppLayout projects={projects}>
        <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6">
          <p className="text-sm text-destructive font-medium">{loadError}</p>
          <Button variant="outline" onClick={reloadProject}>Retry</Button>
        </div>
      </AppLayout>
    )
  }

  if (!project) {
    return (
      <AppLayout projects={projects}>
        <div className="flex flex-1 items-center justify-center p-6">
          <p className="text-muted-foreground">Loading…</p>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout projects={projects}>
      <div className="flex flex-1 flex-col gap-6 p-6">
        <nav className="text-sm text-muted-foreground" aria-label="Breadcrumb">
          <ol className="flex items-center gap-2">
            <li>
              <Link to="/" className="hover:underline">
                Home
              </Link>
            </li>
            <li aria-hidden className="select-none">›</li>
            <li>
              <Link to="/" className="hover:underline">
                Projects
              </Link>
            </li>
            <li aria-hidden className="select-none">›</li>
            <li className="text-foreground font-medium" aria-current="page">
              {project.name}
            </li>
          </ol>
        </nav>
        <div className="group/title flex items-center gap-2">
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          <Button
            variant="ghost"
            size="icon-sm"
            className="opacity-100 md:opacity-0 md:group-hover/title:opacity-100 transition-opacity"
            onClick={openEditDialog}
            aria-label="Edit project"
          >
            <Pencil className="size-4" />
          </Button>
        </div>
        <p className="text-muted-foreground border-b pb-4">Project Description</p>

        <Dialog open={editDialogOpen} onOpenChange={(open) => { setEditDialogOpen(open); if (!open) setEditError(null) }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Project</DialogTitle>
              <DialogDescription>
                Rename the project or delete it.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-project-name">Project Name</Label>
                <Input
                  id="edit-project-name"
                  value={editName}
                  onChange={(e) => { setEditName(e.target.value); setEditError(null) }}
                  onKeyDown={(e) => e.key === "Enter" && saveProjectEdit()}
                  placeholder="Project name"
                />
              </div>
              {editError && (
                <p className="text-sm text-destructive">{editError}</p>
              )}
              <div className="flex justify-between gap-2">
                <Button
                  variant="destructive"
                  onClick={deleteProject}
                >
                  Delete Project
                </Button>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={saveProjectEdit} disabled={!editName.trim() || editSaving}>
                    {editSaving ? "Saving…" : "Save"}
                  </Button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog open={evaluateDialogOpen} onOpenChange={(open) => { setEvaluateDialogOpen(open); if (!open) setReportError(null) }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Evaluate Submittal</DialogTitle>
              <DialogDescription>
                Upload the spec PDF and the submittal PDF to run the full pipeline and LLM audit. Evaluation may take 1–2 minutes.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="eval-spec-pdf">Spec PDF</Label>
                <Input
                  id="eval-spec-pdf"
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setEvalSpecFile(e.target.files?.[0] ?? null)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="eval-submittal-pdf">Submittal PDF</Label>
                <Input
                  id="eval-submittal-pdf"
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setEvalSubmittalFile(e.target.files?.[0] ?? null)}
                />
                {evaluateSubmittal && (
                  <p className="text-xs text-muted-foreground">
                    Use the same file you uploaded as “{evaluateSubmittal.name}” or an updated version.
                  </p>
                )}
              </div>
              {reportError && (
                <p className="text-sm text-destructive">{reportError}</p>
              )}
              <DialogFooter>
                <Button variant="outline" onClick={() => setEvaluateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={submitEvaluate}
                  disabled={!evalSpecFile || !evalSubmittalFile || reportLoading}
                >
                  {reportLoading ? "Evaluating… (1–2 min)" : "Run evaluation"}
                </Button>
              </DialogFooter>
            </div>
          </DialogContent>
        </Dialog>

        <Tabs defaultValue="dashboard">
          <TabsList className="w-fit [&>[data-slot=tabs-trigger]]:flex-initial">
            <TabsTrigger value="dashboard">Project Dashboard</TabsTrigger>
            <TabsTrigger value="reference">Reference Docs</TabsTrigger>
            <TabsTrigger value="submittals">Submittals</TabsTrigger>
            <TabsTrigger value="rfis">RFIs</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            <Card>
              <CardHeader>
                <h2 className="text-lg font-medium">Overview</h2>
              </CardHeader>
              <CardContent className="space-y-2">
                <p><strong>Project:</strong> {project.name}</p>
                <p><strong>Reference documents:</strong> {project.reference_docs?.length ?? 0}</p>
                <p><strong>Submittals:</strong> {project.open_submittals?.length ?? 0} under review, {project.closed_submittals?.length ?? 0} completed</p>
                <p><strong>RFIs:</strong> {project.rfis?.length ?? 0}</p>
                <p className="text-sm text-muted-foreground">Use the other tabs to add reference docs, submittals, and RFIs.</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="reference">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-medium">Reference Documents</h2>
                </CardHeader>
                <CardContent className="space-y-4">
                  {(project.reference_docs ?? []).map((ref) => (
                    <div key={ref.id ?? ref.name} className="rounded-lg border p-4">
                      <p className="font-medium">{ref.name}</p>
                      {ref.csi_division && (
                        <p className="text-sm text-muted-foreground">CSI: {ref.csi_division}</p>
                      )}
                      <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
                        {ref.summary ?? "No description available."}
                      </p>
                    </div>
                  ))}
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-medium">Add a reference document</h2>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">CSI division is detected automatically from the document content when possible.</p>
                  <div>
                    <Label>File (PDF, DOCX, TXT)</Label>
                    <Input
                      type="file"
                      accept=".pdf,.docx,.txt"
                      onChange={(e) => setRefFile(e.target.files?.[0] ?? null)}
                    />
                  </div>
                  <Button onClick={addReferenceDoc} disabled={!refFile || uploading}>
                    <Upload className="mr-2 size-4" />
                    {uploading ? "Uploading…" : "Save to project"}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="submittals">
            {reportError && (
              <div className="mb-4 flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
                <AlertCircle className="size-4 shrink-0" />
                {reportError}
              </div>
            )}
            <div className="flex gap-2 mb-4">
              <Button
                variant={submittalsView === "open" ? "default" : "outline"}
                size="sm"
                onClick={() => setSubmittalsView("open")}
              >
                Under Review
              </Button>
              <Button
                variant={submittalsView === "closed" ? "default" : "outline"}
                size="sm"
                onClick={() => setSubmittalsView("closed")}
              >
                Completed
              </Button>
            </div>
            {submittalsView === "open" ? (
              <>
                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-medium">Under Review</h2>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {(project.open_submittals ?? []).map((sub) => (
                      <div key={sub.id ?? sub.name} className="rounded-lg border p-4">
                        <p className="font-medium">{sub.name}</p>
                        <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
                          {sub.summary ?? "No description available."}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => openEvaluateDialog(sub)}
                            disabled={reportLoading}
                          >
                            <FileCheck className="mr-2 size-4" />
                            {reportLoading ? "Evaluating… (1–2 min)" : "Evaluate"}
                          </Button>
                          {sub.evaluation_report && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openReport(sub.evaluation_report!, sub.name)}
                            >
                              View report
                            </Button>
                          )}
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => sub.id && completeSubmittal(sub.id)}
                          >
                            Mark completed
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
                <Card className="mt-6">
                  <CardHeader>
                    <h2 className="text-lg font-medium">Upload a Submittal</h2>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground">CSI division is detected automatically from the document content when possible.</p>
                    <div>
                      <Label>File (PDF, DOCX)</Label>
                      <Input
                        type="file"
                        accept=".pdf,.docx"
                        onChange={(e) => setSubFile(e.target.files?.[0] ?? null)}
                      />
                    </div>
                    <Button onClick={addSubmittal} disabled={!subFile || uploading}>
                      <Upload className="mr-2 size-4" />
                      {uploading ? "Uploading…" : "Add to Under Review"}
                    </Button>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-medium">Completed</h2>
                </CardHeader>
                <CardContent className="space-y-4">
                  {(project.closed_submittals ?? []).length === 0 ? (
                    <p className="text-muted-foreground">Closed submittals will appear here.</p>
                  ) : (
                    (project.closed_submittals ?? []).map((sub) => (
                      <div key={sub.id ?? sub.name} className="rounded-lg border p-4">
                        <p className="font-medium">{sub.name}</p>
                        <p className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
                          {sub.summary ?? "No description available."}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => openEvaluateDialog(sub)}
                            disabled={reportLoading}
                          >
                            <FileCheck className="mr-2 size-4" />
                            {reportLoading ? "Evaluating… (1–2 min)" : "Evaluate"}
                          </Button>
                          {sub.evaluation_report && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openReport(sub.evaluation_report!, sub.name)}
                            >
                              View report
                            </Button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="rfis">
            <Card>
              <CardHeader>
                <h2 className="text-lg font-medium">RFIs</h2>
              </CardHeader>
              <CardContent className="space-y-4">
                {(project.rfis ?? []).map((rfi) => (
                  <div key={rfi.id ?? rfi.title} className="rounded-lg border p-4">
                    <p className="font-medium">{rfi.title} — {rfi.status}</p>
                    <p className="text-sm text-muted-foreground">Date: {rfi.date}</p>
                    <p className="mt-2">{rfi.description}</p>
                  </div>
                ))}
                <Dialog open={rfiOpen} onOpenChange={setRfiOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline">Add RFI</Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add RFI</DialogTitle>
                      <DialogDescription>Request for Information</DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div>
                        <Label>Title</Label>
                        <Input value={rfiTitle} onChange={(e) => setRfiTitle(e.target.value)} placeholder="Title" />
                      </div>
                      <div>
                        <Label>Description</Label>
                        <Textarea value={rfiDesc} onChange={(e) => setRfiDesc(e.target.value)} placeholder="Description" />
                      </div>
                      <div>
                        <Label>Status</Label>
                        <Select value={rfiStatus} onValueChange={setRfiStatus}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Open">Open</SelectItem>
                            <SelectItem value="Answered">Answered</SelectItem>
                            <SelectItem value="Closed">Closed</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <Button onClick={addRfi}>Add RFI</Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <Dialog
          open={reportDialogOpen}
          onOpenChange={(open) => {
            setReportDialogOpen(open)
            if (!open) setReportError(null)
          }}
        >
          <DialogContent
            showCloseButton={false}
            className="!flex !h-[90vh] !max-h-[90vh] !w-[95vw] !max-w-[95vw] !flex-col !gap-0 !p-0"
          >
            <DialogHeader className="shrink-0 border-b px-6 py-4">
              <DialogTitle>Submittal evaluation: {reportSubmittalName}</DialogTitle>
              <DialogDescription>Technical audit against project specifications</DialogDescription>
            </DialogHeader>
            <div className="min-h-0 flex-1 overflow-y-auto scrollbar-hide px-6 py-4">
              {reportData && (
                <div className="space-y-6">
                  {/* Suggested Action */}
                  <div className="rounded-lg border p-4">
                    <h3 className="mb-2 text-sm font-medium text-muted-foreground">Suggested action</h3>
                    <SuggestedActionBadge action={reportData.suggested_action} />
                  </div>

                  {/* Executive Summary Table */}
                  <div className="rounded-lg border p-4">
                    <h3 className="mb-3 text-sm font-medium">Executive summary</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="pb-2 pr-4 text-left font-medium">Feature</th>
                            <th className="pb-2 pr-4 text-left font-medium">Requirement (Spec)</th>
                            <th className="pb-2 pr-4 text-left font-medium">Submitted value</th>
                            <th className="pb-2 text-left font-medium">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reportData.summary_table.map((row, i) => (
                            <tr key={i} className="border-b last:border-0">
                              <td className="py-2 pr-4">{row.feature}</td>
                              <td className="py-2 pr-4">{row.spec_requirement}</td>
                              <td className="py-2 pr-4">{row.submitted_value}</td>
                              <td className="py-2">
                                <StatusBadge status={row.status} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Compliance narrative */}
                  {reportData.compliance_narrative && (
                    <div className="rounded-lg border p-4">
                      <h3 className="mb-2 text-sm font-medium">Compliance narrative</h3>
                      <p className="text-sm">{reportData.compliance_narrative}</p>
                    </div>
                  )}

                  {/* Missing information */}
                  {reportData.missing_information.length > 0 && (
                    <div className="rounded-lg border p-4">
                      <h3 className="mb-2 text-sm font-medium">Missing information</h3>
                      <ul className="list-inside list-disc text-sm">
                        {reportData.missing_information.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Critical deviations */}
                  {reportData.critical_deviations.length > 0 && (
                    <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4">
                      <h3 className="mb-2 text-sm font-medium text-destructive">Critical deviations</h3>
                      <ul className="list-inside list-disc text-sm">
                        {reportData.critical_deviations.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Detailed discrepancies */}
                  {reportData.detailed_discrepancies.length > 0 && (
                    <div className="rounded-lg border p-4">
                      <h3 className="mb-2 text-sm font-medium">Detailed discrepancies</h3>
                      <ul className="space-y-2 text-sm">
                        {reportData.detailed_discrepancies.map((d, i) => (
                          <li key={i} className="rounded border p-2">
                            <span className="font-medium">{d.item}</span>
                            {d.risk && <p className="mt-1 text-muted-foreground">{d.risk}</p>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
            <DialogFooter className="shrink-0 border-t px-6 py-4">
              <Button variant="outline" onClick={() => setReportDialogOpen(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    Pass: { label: "Pass", className: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" },
    Fail: { label: "Fail", className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" },
    Deviated: { label: "Deviated", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400" },
    Missing: { label: "Missing", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400" },
  }
  const s = map[status] ?? { label: status, className: "bg-muted text-muted-foreground" }
  return <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${s.className}`}>{s.label}</span>
}

function SuggestedActionBadge({ action }: { action: string }) {
  const map: Record<string, { label: string; className: string }> = {
    APPROVED: { label: "Approve", className: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" },
    APPROVED_AS_NOTED: { label: "Approve as Noted", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400" },
    REVISE_AND_RESUBMIT: { label: "Revise and Resubmit", className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" },
    REJECTED: { label: "Rejected", className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" },
  }
  const s = map[action] ?? { label: action, className: "bg-muted text-muted-foreground" }
  return <span className={`inline-flex rounded-lg px-3 py-1.5 text-sm font-semibold ${s.className}`}>{s.label}</span>
}
