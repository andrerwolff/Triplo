// In dev, use same origin so Vite proxy forwards /api to backend (no CORS, no timeout issues).
const API_BASE =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "" : "http://localhost:8000")

export type ReferenceDoc = {
  id?: string
  name: string
  csi_division?: string | null
  extracted_text: string
  summary?: string | null
}

export type EvaluationReport = {
  summary_table: Array<{
    feature: string
    spec_requirement: string
    submitted_value: string
    status: "Pass" | "Fail" | "Deviated" | "Missing"
  }>
  compliance_narrative: string
  missing_information: string[]
  critical_deviations: string[]
  detailed_discrepancies: Array<{ item: string; risk: string }>
  suggested_action: "APPROVED" | "APPROVED_AS_NOTED" | "REVISE_AND_RESUBMIT" | "REJECTED"
}

export type Submittal = {
  id?: string
  name: string
  csi_division?: string | null
  extracted_text: string
  summary?: string | null
  evaluation_report?: EvaluationReport | null
  evaluated_at?: string | null
}

export type RFI = {
  id?: string
  title: string
  description: string
  status: string
  date: string
}

export type Project = {
  id: string
  name: string
  open_submittals: Submittal[]
  closed_submittals: Submittal[]
  reference_docs: ReferenceDoc[]
  rfis: RFI[]
}

export type ProjectsResponse = { projects: Project[] }
export type CSIResponse = { divisions: string[] }

/** Timeout for normal API calls (list/get/update). Long-running evaluate uses proxy timeout. */
const REQUEST_TIMEOUT_MS = 15_000

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase()
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }
  if (method !== "GET" && method !== "HEAD" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json"
  }
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      signal: options.signal ?? controller.signal,
    })
  } catch (e) {
    clearTimeout(timeoutId)
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error(
        `Request timed out. Is the backend running at ${API_BASE || "localhost:8000"}? Start it with: cd backend && python3 -m uvicorn app.main:app --reload --port 8000`
      )
    }
    throw e
  }
  clearTimeout(timeoutId)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }
  return res.json()
}

export const api = {
  getProjects: () => request<ProjectsResponse>("/api/projects"),
  getProject: (id: string) => request<Project>(`/api/projects/${id}`),
  createProject: (name: string) => {
    const form = new FormData()
    form.append("name", name)
    return fetch(`${API_BASE}/api/projects`, {
      method: "POST",
      body: form,
    })
      .then(async (r) => {
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }))
          throw new Error(err.detail ?? r.statusText)
        }
        return r.json() as Promise<Project>
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err)
        if (msg === "Failed to fetch" || msg.includes("NetworkError") || msg.includes("Load failed")) {
          throw new Error(`Cannot reach the backend at ${API_BASE}. Start it with: cd backend && python3 -m uvicorn app.main:app --reload --port 8000`)
        }
        throw err
      })
  },
  updateProject: (id: string, data: { name: string }) =>
    request<Project>(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteProject: (id: string) =>
    request<{ ok: boolean }>(`/api/projects/${id}`, { method: "DELETE" }),
  addReferenceDoc: (projectId: string, file: File, csiDivision: string) => {
    const form = new FormData()
    form.append("file", file)
    form.append("csi_division", csiDivision)
    return fetch(`${API_BASE}/api/projects/${projectId}/reference-docs`, {
      method: "POST",
      body: form,
    }).then(async (r) => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }))
        throw new Error(err.detail ?? r.statusText)
      }
      return r.json() as Promise<Project>
    })
  },
  addSubmittal: (projectId: string, file: File, csiDivision: string) => {
    const form = new FormData()
    form.append("file", file)
    form.append("csi_division", csiDivision)
    return fetch(`${API_BASE}/api/projects/${projectId}/submittals`, {
      method: "POST",
      body: form,
    }).then(async (r) => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }))
        throw new Error(err.detail ?? r.statusText)
      }
      return r.json() as Promise<Project>
    })
  },
  /** Evaluate using pipeline state (verified_requirements + filtered_submittal_data). Use when you have state from POST /api/pipeline/audit. */
  evaluateSubmittalWithState: (
    projectId: string,
    submittalId: string,
    data: { verified_requirements: unknown[]; filtered_submittal_data: unknown[]; spec_section?: string }
  ) =>
    request<{ report: EvaluationReport; evaluated_at: string; project: Project }>(
      `/api/projects/${projectId}/submittals/${submittalId}/evaluate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    ),

  /** Evaluate by uploading spec PDF + submittal PDF. Runs full pipeline then LLM audit. */
  evaluateSubmittalWithPdfs: (
    projectId: string,
    submittalId: string,
    specPdf: File,
    submittalPdf: File,
    options?: { spec_section?: string }
  ) => {
    const form = new FormData()
    form.append("spec_pdf", specPdf)
    form.append("submittal_pdf", submittalPdf)
    if (options?.spec_section) form.append("spec_section", options.spec_section)
    return fetch(`${API_BASE}/api/projects/${projectId}/submittals/${submittalId}/evaluate`, {
      method: "POST",
      body: form,
    })
      .then(async (r) => {
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }))
          throw new Error(err.detail ?? r.statusText)
        }
        return r.json() as Promise<{
          report: EvaluationReport
          evaluated_at: string
          project: Project
        }>
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err)
        if (msg === "Failed to fetch" || msg.includes("NetworkError") || msg.includes("Load failed")) {
          throw new Error(
            `Cannot reach the backend at ${API_BASE}. Make sure it is running. Evaluate can take 1–2 minutes—please wait.`
          )
        }
        throw err
      })
  },

  evaluateSubmittal: (
    projectId: string,
    submittalId: string,
    options?: { spec_section?: string; reference_doc_ids?: string[] }
  ) => {
    const body = options
      ? JSON.stringify(
          options.reference_doc_ids
            ? { spec_section: options.spec_section, reference_doc_ids: options.reference_doc_ids }
            : options.spec_section
              ? { spec_section: options.spec_section }
              : {}
        )
      : undefined
    return fetch(`${API_BASE}/api/projects/${projectId}/submittals/${submittalId}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ?? "{}",
    })
      .then(async (r) => {
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }))
          throw new Error(err.detail ?? r.statusText)
        }
        return r.json() as Promise<{
          report: EvaluationReport
          evaluated_at: string
          project: Project
        }>
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err)
        if (msg === "Failed to fetch" || msg.includes("NetworkError") || msg.includes("Load failed")) {
          throw new Error(
            `Cannot reach the backend at ${API_BASE}. Make sure it is running. Evaluate can take 1–2 minutes—please wait.`
          )
        }
        throw err
      })
  },
  completeSubmittal: (projectId: string, submittalId: string) =>
    request<Project>(
      `/api/projects/${projectId}/submittals/${submittalId}/complete`,
      { method: "POST" }
    ),
  addRfi: (
    projectId: string,
    data: { title: string; description: string; status: string }
  ) => {
    const form = new FormData()
    form.append("title", data.title)
    form.append("description", data.description)
    form.append("status", data.status)
    return fetch(`${API_BASE}/api/projects/${projectId}/rfis`, {
      method: "POST",
      body: form,
    }).then(async (r) => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }))
        throw new Error(err.detail ?? r.statusText)
      }
      return r.json() as Promise<Project>
    })
  },
  getCsiDivisions: () =>
    request<CSIResponse>("/api/constants/csi-divisions"),
}
