export type SentimentLevel = "amazing" | "good" | "neutral" | "poor" | "terrible";

export interface ApiWearableData {
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
    heartRate: number[];
    stepCount: number[];
  };
  sentiment: SentimentLevel;
  privateNotes: string;
  researchTopic: string;
  researchContent: string[];
  doctorNotes: DoctorNote[];
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
