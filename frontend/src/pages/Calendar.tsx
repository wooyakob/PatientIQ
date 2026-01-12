import { Header } from '@/components/Header';
import { Calendar as CalendarIcon, Clock, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getDoctorAppointments, getPreVisitQuestionnaireStatus } from '@/lib/api';

interface Appointment {
  id: string;
  patientId: string;
  patientName: string;
  patientAvatar: string;
  date: string;
  time: string;
  type: string;
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

export default function Calendar() {
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
    return {
    id: a.id,
    patientId,
    patientName: a.patient_name,
    patientAvatar: toInitials(a.patient_name),
    date: a.appointment_date,
    time: formatTimeHHMM(a.appointment_time),
    type: formatAppointmentType(a.appointment_type),
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

  const groupedAppointments = groupAppointmentsByDate(appointments);
  const sortedDates = Object.keys(groupedAppointments).sort();

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
                          <div className="flex items-center gap-2 mb-3">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium text-foreground">Pre-Visit Questionnaires</span>
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
    </div>
  );
}
