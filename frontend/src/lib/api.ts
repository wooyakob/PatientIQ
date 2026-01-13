export type SentimentLevel = "amazing" | "good" | "neutral" | "poor" | "terrible";

export interface ApiWearableData {
  timestamps?: string[];
  heart_rate: number[];
  step_count: number[];
}

export interface ApiPatient {
  id: string;
  name: string;
  age: number;
  gender: string;
  condition: string;
  avatar: string;
  last_visit: string;
  next_appointment: string;
  wearable_data: ApiWearableData;
  sentiment: SentimentLevel;
  private_notes: string;
  research_topic: string;
  research_content: string[];
}

export interface DoctorNote {
  id: string;
  date: string;
  time: string;
  content: string;
}

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: string;
  condition: string;
  avatar: string;
  lastVisit: string;
  nextAppointment: string;
  wearableData: {
    timestamps: string[];
    heartRate: number[];
    stepCount: number[];
  };
  sentiment: SentimentLevel;
  privateNotes: string;
  researchTopic: string;
  researchContent: string[];
  doctorNotes: DoctorNote[];
}

export interface ApiStaffMessage {
  id: string;
  message_type: "private" | "public";
  from_id: string;
  from_name: string;
  to_id?: string;
  to_name?: string;
  subject: string;
  content: string;
  timestamp: string;
  read?: boolean;
  priority?: string;
}

export interface ApiAppointment {
  id: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  doctor_name: string;
  appointment_date: string;
  appointment_time: string;
  appointment_type: string;
  status: string;
  duration_minutes?: number;
  notes?: string;
}

export interface ApiQuestionnaireStatus {
  patient_id: string;
  exists: boolean;
  completed: boolean;
  date_completed?: string | null;
}

export async function getPreVisitQuestionnaireStatus(
  patientIds: string[]
): Promise<Record<string, ApiQuestionnaireStatus>> {
  const result = await apiFetch<{ statuses: ApiQuestionnaireStatus[] }>(
    "/api/questionnaires/pre-visit/status",
    {
      method: "POST",
      body: JSON.stringify({ patient_ids: patientIds }),
    }
  );

  const map: Record<string, ApiQuestionnaireStatus> = {};
  for (const s of result.statuses ?? []) {
    map[String(s.patient_id)] = s;
  }
  return map;
}

export async function getPreVisitQuestionnaire(patientId: string): Promise<any> {
  return apiFetch<any>(
    `/api/questionnaires/pre-visit/${encodeURIComponent(String(patientId))}`
  );
}

export async function getDoctorAppointments(
  doctorId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<ApiAppointment[]> {
  const search = new URLSearchParams();
  if (params?.start_date) search.set("start_date", params.start_date);
  if (params?.end_date) search.set("end_date", params.end_date);

  const qs = search.toString();
  const result = await apiFetch<{ doctor_id: string; appointments: ApiAppointment[] }>(
    `/api/appointments/doctor/${encodeURIComponent(doctorId)}${qs ? `?${qs}` : ""}`
  );

  return result.appointments ?? [];
}

export async function getPrivateMessages(doctorId: string, limit: number = 50): Promise<ApiStaffMessage[]> {
  const result = await apiFetch<{ doctor_id: string; messages: ApiStaffMessage[] }>(
    `/api/messages/private/${encodeURIComponent(doctorId)}?limit=${encodeURIComponent(String(limit))}`
  );
  return result.messages ?? [];
}

export async function getPublicMessages(limit: number = 50): Promise<ApiStaffMessage[]> {
  const result = await apiFetch<{ messages: ApiStaffMessage[] }>(
    `/api/messages/public?limit=${encodeURIComponent(String(limit))}`
  );
  return result.messages ?? [];
}

export async function sendPrivateMessage(payload: {
  to_id: string;
  to_name: string;
  subject: string;
  content: string;
  priority?: string;
}): Promise<{ message: string; id: string }> {
  return apiFetch<{ message: string; id: string }>("/api/messages/private", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendPublicMessage(payload: {
  subject: string;
  content: string;
  priority?: string;
}): Promise<{ message: string; id: string }> {
  return apiFetch<{ message: string; id: string }>("/api/messages/public", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getPatientWearables( 
  patientId: string,
  days: number = 30
): Promise<{ timestamps: string[]; heartRate: number[]; stepCount: number[] }> {
  const result = await apiFetch<ApiWearableData>(
    `/api/patients/${encodeURIComponent(patientId)}/wearables?days=${encodeURIComponent(String(days))}`
  );

  return {
    timestamps: result?.timestamps ?? [],
    heartRate: result?.heart_rate ?? [],
    stepCount: result?.step_count ?? [],
  };
}

export function toLocalDateOnlyString(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseDateOnlyToLocalDate(dateString: string): Date | null {
  const s = (dateString ?? "").trim();
  if (!s) return null;

  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const d = new Date(`${s}T00:00:00`);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDateOnlyForDisplay(dateString: string): string {
  const d = parseDateOnlyToLocalDate(dateString);
  return d
    ? d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "";
}

const toPatient = (api: ApiPatient, doctorNotes: DoctorNote[] = []): Patient => {
  return {
    id: api.id,
    name: api.name,
    age: api.age,
    gender: api.gender,
    condition: api.condition,
    avatar: api.avatar,
    lastVisit: api.last_visit,
    nextAppointment: api.next_appointment,
    wearableData: {
      timestamps: api.wearable_data?.timestamps ?? [],
      heartRate: api.wearable_data?.heart_rate ?? [],
      stepCount: api.wearable_data?.step_count ?? [],
    },
    sentiment: api.sentiment,
    privateNotes: api.private_notes,
    researchTopic: api.research_topic ?? "",
    researchContent: api.research_content ?? [],
    doctorNotes,
  };
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return (await res.json()) as T;
}

export async function getPatients(): Promise<Patient[]> {
  const apiPatients = await apiFetch<ApiPatient[]>("/api/patients");
  return apiPatients.map((p) => toPatient(p));
}

export async function getPatient(patientId: string): Promise<Patient> {
  const apiPatient = await apiFetch<ApiPatient>(`/api/patients/${encodeURIComponent(patientId)}`);
  return toPatient(apiPatient);
}

export async function getDoctorNotes(patientId: string): Promise<DoctorNote[]> {
  const result = await apiFetch<{ patient_id: string; notes: any[] }>(
    `/api/patients/${encodeURIComponent(patientId)}/doctor-notes`
  );

  return (result.notes ?? [])
    .map((n, idx) => ({
      id: String(n.id ?? `${patientId}-${idx}`),
      date: String(n.date ?? ""),
      time: String(n.time ?? ""),
      content: String(n.content ?? ""),
    }))
    .filter((n) => n.date.trim().length > 0 && n.content.trim().length > 0);
}

export async function getPatientWithNotes(patientId: string): Promise<Patient> {
  const [patient, notes] = await Promise.all([getPatient(patientId), getDoctorNotes(patientId)]);
  return { ...patient, doctorNotes: notes };
}

export interface SaveDoctorNoteRequest {
  visit_date: string;
  doctor_name: string;
  doctor_id: string;
  visit_notes: string;
  patient_name: string;
  patient_id: string;
}

export async function saveDoctorNote(note: SaveDoctorNoteRequest): Promise<{ message: string; note_id: string }> {
  return apiFetch<{ message: string; note_id: string }>("/api/doctor-notes", {
    method: "POST",
    body: JSON.stringify(note),
  });
}

export async function deleteDoctorNote(noteId: string): Promise<{ message: string; note_id: string }> {
  return apiFetch<{ message: string; note_id: string }>(`/api/doctor-notes/${encodeURIComponent(noteId)}`, {
    method: "DELETE",
  });
}


// Research types
export interface ResearchPaper {
  title: string;
  author: string;
  article_citation: string;
  pmc_link: string;
}

export interface ResearchResult {
  patient_id: string;
  patient_name: string;
  condition: string;
  question: string;
  papers: ResearchPaper[];
  answer: string;
}

// Medical Research Agent API
export async function getPatientResearch(patientId: string, question?: string): Promise<ResearchResult> {
  const params = question ? `?question=${encodeURIComponent(question)}` : '';
  return apiFetch<ResearchResult>(`/api/patients/${patientId}/research${params}`);
}

export async function askResearchQuestion(patientId: string, question: string): Promise<ResearchResult> {
  return apiFetch<ResearchResult>(`/api/patients/${patientId}/research/ask`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

export async function saveResearchAnswer(
  question: string,
  answer: string,
  rating?: number
): Promise<{ message: string; answer_id: string }> {
  return apiFetch('/api/research/answers', {
    method: 'POST',
    body: JSON.stringify({
      question_asked: question,
      answer_provided: answer,
      answer_rating: rating,
    }),
  });
}

export async function updateAnswerRating(
  answerId: string,
  rating: number
): Promise<{ message: string; answer_id: string; rating: number }> {
  return apiFetch(`/api/research/answers/${answerId}/rating`, {
    method: 'PATCH',
    body: JSON.stringify({ rating }),
  });
}
