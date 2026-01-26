import { Header } from '@/components/Header';
import { Calendar as CalendarIcon, Clock, FileText, CheckCircle2, AlertCircle, Sparkles, X, Loader2, Pill, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { getDoctorAppointments, getPreVisitQuestionnaireStatus, getPreVisitSummary, PreVisitSummary } from '@/lib/api';

interface Appointment {
  id: string;
  patientId: string;
  patientName: string;
  patientAvatar: string;
  date: string;
  time: string;
  type: string;
  startMs: number;
  questionnaires: {
    name: string;
    exists: boolean;
    completed: boolean;
    completedAt?: string;
  }[];
}

const currentDoctorId = '1';

function groupAppointmentsByDate(appointments: Appointment[]) {
  return appointments.reduce((groups, appointment) => {
    const date = appointment.date;
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(appointment);
    return groups;
  }, {} as Record<string, Appointment[]>);
}

function formatDate(dateString: string) {
  const date = new Date(dateString);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (dateString === today.toISOString().split('T')[0]) {
    return 'Today';
  } else if (dateString === tomorrow.toISOString().split('T')[0]) {
    return 'Tomorrow';
  }

  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

function toInitials(name: string) {
  const parts = (name ?? '').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatTimeHHMM(time: string) {
  const t = (time ?? '').trim();
  const m = t.match(/^(\d{1,2}):(\d{2})$/);
  if (!m) return t;

  const hours = Number(m[1]);
  const minutes = Number(m[2]);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return t;

  const d = new Date();
  d.setHours(hours, minutes, 0, 0);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function parseAppointmentStartMs(dateString: string, timeString: string): number {
  const d = String(dateString ?? '').trim();
  if (!d) return Number.NaN;

  const t = String(timeString ?? '').trim();
  const m = t.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) {
    const fallback = new Date(`${d}T00:00:00`);
    return fallback.getTime();
  }

  const hh = String(m[1]).padStart(2, '0');
  const mm = String(m[2]).padStart(2, '0');
  const ss = String(m[3] ?? '00').padStart(2, '0');
  const dt = new Date(`${d}T${hh}:${mm}:${ss}`);
  return dt.getTime();
}

function formatAppointmentType(t: string) {
  const s = (t ?? '').trim().toLowerCase();
  if (!s) return '';

  const map: Record<string, string> = {
    'follow-up': 'Follow-up',
    consultation: 'Consultation',
    emergency: 'Emergency',
    routine: 'Routine',
    urgent: 'Urgent',
  };

  return map[s] ?? s.charAt(0).toUpperCase() + s.slice(1);
}

function PreVisitSummaryModal({
  patientId,
  patientName,
  onClose
}: {
  patientId: string;
  patientName: string;
  onClose: () => void;
}) {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['previsit-summary', patientId],
    queryFn: () => getPreVisitSummary(patientId),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-background rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold text-foreground">Pre-Visit Summary</h2>
              <p className="text-sm text-muted-foreground">{patientName}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-muted rounded-lg transition-colors">
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-muted-foreground">Generating pre-visit summary...</span>
            </div>
          )}

          {error && (
            <div className="text-center py-12 text-red-500">
              Failed to load summary. Please try again.
            </div>
          )}

          {summary && (
            <div className="space-y-5">
              {/* Clinical Summary - Highlighted at top */}
              <div className="bg-gradient-to-br from-primary/10 to-primary/5 border-l-4 border-primary rounded-lg p-4">
                <h3 className="text-sm font-semibold text-primary mb-2.5 flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  Clinical Summary
                </h3>
                <p className="text-foreground leading-relaxed text-[15px]">{summary.clinical_summary}</p>
              </div>

              <div className="h-px bg-border"></div>

              {/* Two Column Layout for Key Info */}
              <div className="grid md:grid-cols-2 gap-5">
                {/* Left Column */}
                <div className="space-y-5">
                  {/* Medications */}
                  {summary.current_medications && summary.current_medications.length > 0 && (
                    <div className="bg-card border border-border rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <Pill className="h-4 w-4 text-blue-500" />
                        Current Medications
                        <span className="ml-auto text-xs font-normal text-muted-foreground">
                          {summary.current_medications.length} active
                        </span>
                      </h3>
                      <div className="space-y-2.5">
                        {summary.current_medications.map((med, idx) => (
                          <div key={idx} className="bg-muted/30 rounded-md p-2.5 text-sm border border-border/50">
                            <div className="font-medium text-foreground">{med.name}</div>
                            <div className="text-muted-foreground text-xs mt-1 flex items-center gap-2">
                              <span className="bg-background px-2 py-0.5 rounded">{med.dosage}</span>
                              <span>•</span>
                              <span>{med.frequency}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key Symptoms */}
                  {summary.key_symptoms && summary.key_symptoms.length > 0 && (
                    <div className="bg-card border border-border rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <svg className="h-4 w-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Key Symptoms
                      </h3>
                      <ul className="space-y-2">
                        {summary.key_symptoms.map((symptom, idx) => (
                          <li key={idx} className="flex items-start gap-2.5 text-sm">
                            <span className="h-1.5 w-1.5 rounded-full bg-primary mt-2 flex-shrink-0"></span>
                            <span className="text-foreground flex-1">{symptom}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Right Column */}
                <div className="space-y-5">
                  {/* Allergies - Critical Info */}
                  {(summary.allergies.drug.length > 0 || summary.allergies.food.length > 0 || summary.allergies.environmental.length > 0) && (
                    <div className="bg-card border border-red-500/30 rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                        <span className="text-red-600 dark:text-red-400">Allergies</span>
                      </h3>
                      <div className="space-y-2">
                        {summary.allergies.drug.length > 0 && (
                          <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-md p-2.5 text-sm">
                            <div className="font-semibold text-red-700 dark:text-red-400 text-xs uppercase tracking-wide mb-1">Drug Allergies</div>
                            <div className="text-red-900 dark:text-red-300">{summary.allergies.drug.join(', ')}</div>
                          </div>
                        )}
                        {summary.allergies.food.length > 0 && (
                          <div className="bg-muted/50 border border-border/50 rounded-md p-2.5 text-sm">
                            <div className="font-medium text-foreground text-xs uppercase tracking-wide mb-1">Food</div>
                            <div className="text-muted-foreground">{summary.allergies.food.join(', ')}</div>
                          </div>
                        )}
                        {summary.allergies.environmental.length > 0 && (
                          <div className="bg-muted/50 border border-border/50 rounded-md p-2.5 text-sm">
                            <div className="font-medium text-foreground text-xs uppercase tracking-wide mb-1">Environmental</div>
                            <div className="text-muted-foreground">{summary.allergies.environmental.join(', ')}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Patient Concerns/Questions */}
                  {summary.patient_concerns && summary.patient_concerns.length > 0 && (
                    <div className="bg-card border border-border rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <svg className="h-4 w-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Patient Questions
                        <span className="ml-auto text-xs font-normal text-muted-foreground">
                          {summary.patient_concerns.length} questions
                        </span>
                      </h3>
                      <ul className="space-y-2.5">
                        {summary.patient_concerns.map((concern, idx) => (
                          <li key={idx} className="flex items-start gap-2.5 text-sm bg-muted/20 rounded-md p-2">
                            <span className="flex-shrink-0 h-5 w-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-medium">
                              {idx + 1}
                            </span>
                            <span className="text-foreground flex-1 pt-0.5">{concern}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {/* Recent Doctor Note - Full Width at Bottom */}
              {summary.recent_note_summary && (
                <div className="bg-card border border-border rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                    <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Recent Doctor Note
                  </h3>
                  <div className="bg-muted/30 border border-border/50 rounded-md p-3 text-sm text-foreground leading-relaxed italic">
                    {summary.recent_note_summary}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Calendar() {
  const [summaryModal, setSummaryModal] = useState<{ patientId: string; patientName: string } | null>(null);

  const { data: apiAppointments } = useQuery({
    queryKey: ['appointments', 'doctor', currentDoctorId],
    queryFn: () => getDoctorAppointments(currentDoctorId),
  });

  const patientIds = Array.from(
    new Set((apiAppointments ?? []).map((a) => String(a.patient_id)).filter(Boolean))
  ).sort();

  const { data: questionnaireStatusByPatient } = useQuery({
    queryKey: ['questionnaires', 'pre-visit', 'status', patientIds.join(',')],
    queryFn: () => getPreVisitQuestionnaireStatus(patientIds),
    enabled: patientIds.length > 0,
  });

  const appointments: Appointment[] = (apiAppointments ?? []).map((a) => {
    const patientId = String(a.patient_id);
    const status = questionnaireStatusByPatient?.[patientId];
    const startMs = parseAppointmentStartMs(a.appointment_date, a.appointment_time);
    return {
      id: a.id,
      patientId,
      patientName: a.patient_name,
      patientAvatar: toInitials(a.patient_name),
      date: a.appointment_date,
      time: formatTimeHHMM(a.appointment_time),
      type: formatAppointmentType(a.appointment_type),
      startMs,
      questionnaires: [
        {
          name: 'Pre-Visit Questionnaire',
          exists: Boolean(status?.exists),
          completed: Boolean(status?.completed),
          completedAt: status?.date_completed ?? undefined,
        },
      ],
    };
  });

  const nowMs = Date.now();
  const sortedAppointments = [...appointments].sort((a, b) => {
    const aIsPast = a.startMs < nowMs;
    const bIsPast = b.startMs < nowMs;

    if (aIsPast !== bIsPast) return aIsPast ? 1 : -1;

    // Upcoming: ascending (soonest first). Past: descending (most recent first).
    if (!aIsPast && !bIsPast) return a.startMs - b.startMs;
    return b.startMs - a.startMs;
  });

  const groupedAppointments = groupAppointmentsByDate(sortedAppointments);
  for (const date of Object.keys(groupedAppointments)) {
    groupedAppointments[date].sort((a, b) => a.startMs - b.startMs);
  }
  const sortedDates = Array.from(new Set(sortedAppointments.map((a) => a.date)));

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="gradient-primary p-2 rounded-xl">
              <CalendarIcon className="h-5 w-5 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-semibold text-foreground">Appointment Calendar</h1>
          </div>
          <p className="text-muted-foreground ml-12">Upcoming patient visits and pre-visit questionnaire status</p>
        </div>

        <div className="space-y-8">
          {sortedDates.map((date) => (
            <div key={date}>
              <h2 className="text-lg font-medium text-foreground mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-primary" />
                {formatDate(date)}
              </h2>
              
              <div className="space-y-4">
                {groupedAppointments[date].map((appointment) => {
                  const completedCount = appointment.questionnaires.filter(q => q.completed).length;
                  const totalCount = appointment.questionnaires.length;
                  const allCompleted = totalCount > 0 && completedCount === totalCount;
                  
                  return (
                    <div
                      key={appointment.id}
                      className="glass-card neo-shadow rounded-2xl p-5 hover:shadow-lg transition-all duration-300"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-4">
                          <Link
                            to={`/patient/${appointment.patientId}`}
                            className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center text-primary-foreground font-semibold shrink-0 hover:scale-105 transition-transform"
                          >
                            {appointment.patientAvatar}
                          </Link>
                          
                          <div>
                            <Link
                              to={`/patient/${appointment.patientId}`}
                              className="font-medium text-foreground hover:text-primary transition-colors"
                            >
                              {appointment.patientName}
                            </Link>
                            <p className="text-sm text-muted-foreground">{appointment.type}</p>
                            
                            <div className="flex items-center gap-4 mt-2">
                              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                                <Clock className="h-4 w-4" />
                                <span>{appointment.time}</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          {totalCount > 0 ? (
                            <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${
                              allCompleted 
                                ? 'bg-green-500/10 text-green-600' 
                                : 'bg-amber-500/10 text-amber-600'
                            }`}>
                              {allCompleted ? (
                                <CheckCircle2 className="h-4 w-4" />
                              ) : (
                                <AlertCircle className="h-4 w-4" />
                              )}
                              {completedCount}/{totalCount} Forms
                            </div>
                          ) : (
                            <span className="text-sm text-muted-foreground">No forms required</span>
                          )}
                        </div>
                      </div>

                      {appointment.questionnaires.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-border/50">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <FileText className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm font-medium text-foreground">Pre-Visit Questionnaires</span>
                            </div>
                            {appointment.questionnaires.some(q => q.completed) && (
                              <button
                                onClick={() => setSummaryModal({ patientId: appointment.patientId, patientName: appointment.patientName })}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary bg-primary/10 rounded-lg hover:bg-primary/20 transition-colors"
                              >
                                <Sparkles className="h-3.5 w-3.5" />
                                Pre-Visit Summary
                              </button>
                            )}
                          </div>

                          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                            {appointment.questionnaires.map((questionnaire, index) => (
                              questionnaire.exists ? (
                                <Link
                                  key={index}
                                  to={`/patient/${appointment.patientId}/questionnaires/pre-visit`}
                                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-muted/60 ${
                                    questionnaire.completed
                                      ? 'bg-green-500/5 text-green-700'
                                      : 'bg-muted/50 text-muted-foreground'
                                  }`}
                                >
                                  {questionnaire.completed ? (
                                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                                  ) : (
                                    <div className="w-4 h-4 rounded-full border-2 border-current shrink-0" />
                                  )}
                                  <span className="truncate">{questionnaire.name}</span>
                                </Link>
                              ) : (
                                <div
                                  key={index}
                                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                                    questionnaire.completed
                                      ? 'bg-green-500/5 text-green-700'
                                      : 'bg-muted/50 text-muted-foreground'
                                  }`}
                                >
                                  {questionnaire.completed ? (
                                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                                  ) : (
                                    <div className="w-4 h-4 rounded-full border-2 border-current shrink-0" />
                                  )}
                                  <span className="truncate">{questionnaire.name}</span>
                                </div>
                              )
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </main>

      {summaryModal && (
        <PreVisitSummaryModal
          patientId={summaryModal.patientId}
          patientName={summaryModal.patientName}
          onClose={() => setSummaryModal(null)}
        />
      )}
    </div>
  );
}
