import { Patient } from '@/lib/api';
import { FileText, ExternalLink, Calendar, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

interface DoctorNotesWidgetProps {
  patient: Patient;
}

export function DoctorNotesWidget({ patient }: DoctorNotesWidgetProps) {
  const latestNote = patient.doctorNotes[0];

  return (
    <Link
      to={`/patient/${patient.id}/notes`}
      className="glass-card p-6 block transition-all duration-300 hover:scale-[1.01] hover:shadow-xl group"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="neo-card p-2.5 rounded-xl">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <h3 className="font-semibold text-foreground">Doctor's Notes</h3>
        </div>
        <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {latestNote && (
        <div className="space-y-3">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              {new Date(latestNote.date).toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
              })}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              {latestNote.time}
            </span>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
            {latestNote.content}
          </p>
          <p className="text-xs text-primary font-medium">
            {patient.doctorNotes.length} total note{patient.doctorNotes.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </Link>
  );
}
